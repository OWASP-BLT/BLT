import asyncio
import difflib
import json
import os
import subprocess
import tempfile

from channels.generic.websocket import AsyncWebsocketConsumer
from git import Repo

from website.utils import (
    compare_model_fields,
    cosine_similarity,
    extract_django_models,
    extract_function_signatures_and_content,
    generate_embedding,
)


class SimilarityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept the WebSocket connection
        self.room_group_name = "similarity_check"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group when the WebSocket is closed
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        """
        Handles messages received from the WebSocket.
        Expects a JSON object with type1, type2, repo1, and repo2.
        """
        data = json.loads(text_data)

        type1 = data.get("type1")  # 'github' or 'zip'
        type2 = data.get("type2")  # 'github' or 'zip'
        repo1 = data.get("repo1")  # GitHub URL or ZIP file path
        repo2 = data.get("repo2")  # GitHub URL or ZIP file path

        if not repo1 or not repo2 or not type1 or not type2:
            await self.send(
                json.dumps({"error": "Both repositories and their types are required."})
            )
            return

        if type1 not in ["github", "zip"] or type2 not in ["github", "zip"]:
            await self.send(json.dumps({"error": "Invalid type. Must be 'github' or 'zip'."}))
            return

        try:
            # Create a temporary directory for repository processing
            temp_dir = tempfile.mkdtemp()

            # Download or extract the repositories
            repo1_path = await self.download_or_extract(repo1, type1, temp_dir, "repo1")
            repo2_path = await self.download_or_extract(repo2, type2, temp_dir, "repo2")

            # Process similarity analysis
            matching_details = await self.run_similarity_analysis(repo1_path, repo2_path)

            if not matching_details:
                await self.send(
                    json.dumps(
                        {
                            "status": "error",
                            "error": "No matching details found between the repositories.",
                        }
                    )
                )
                await self.close()
                return

            # Send the result back to the client
            await self.send(json.dumps({"status": "success", "matching_details": matching_details}))
            await self.close()

        except Exception as e:
            # Handle unexpected errors and send an error message
            await self.send(
                json.dumps(
                    {"status": "error", "error": "Please check the repositories and try again."}
                )
            )
            await self.close()

        finally:
            # Cleanup temporary directory
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(temp_dir)

    async def run_similarity_analysis(self, repo1_path, repo2_path):
        """
        Runs the similarity analysis asynchronously.
        """
        try:
            # Use asyncio.to_thread to run the blocking process_similarity_analysis in a separate thread
            var = await asyncio.to_thread(self.process_similarity_analysis, repo1_path, repo2_path)
            return var
        except asyncio.CancelledError:
            raise  # Re-raise the cancellation error to propagate it

    async def download_or_extract(self, source, source_type, temp_dir, repo_name):
        """
        Download or extract the repository based on the type (GitHub or ZIP).
        :param source: GitHub URL or ZIP file path
        :param source_type: "github" or "zip"
        :param temp_dir: Temporary directory for processing
        :param repo_name: Prefix for naming (repo1 or repo2)
        :return: Path to the extracted repository
        """
        dest_path = os.path.join(temp_dir, repo_name)
        if source_type == "github":
            try:
                # Clone the GitHub repository
                process = await self.clone_github_repo(source, dest_path)
                return dest_path
            except subprocess.CalledProcessError as e:
                # Handle errors during the cloning process
                raise Exception(f"Error cloning GitHub repository: {e.stderr.decode('utf-8')}")
            except Exception as e:
                # General error handling for unexpected issues
                raise Exception(f"Unexpected error during GitHub cloning: {str(e)}")

        elif source_type == "zip":
            # Handle ZIP extraction (Add your ZIP handling logic here)
            pass

        return dest_path

    async def clone_github_repo(self, repo_url, dest_path):
        """
        Clones a GitHub repository asynchronously.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, Repo.clone_from, repo_url, dest_path)

    def process_similarity_analysis(self, repo1_path, repo2_path):
        """
        Process the similarity analysis between two repositories.
        :param repo1_path: Path to the first repository
        :param repo2_path: Path to the second repository
        :return: Similarity score and matching details
        """
        try:
            asyncio.run(self.send(json.dumps({"progress": 0, "status": "progress"})))
        except Exception as e:
            return None
        matching_details = {
            "functions": [],
            "models": [],
        }

        # Extract function signatures and content
        functions1 = extract_function_signatures_and_content(repo1_path)
        functions2 = extract_function_signatures_and_content(repo2_path)
        function_text_embeddings = {}
        try:
            asyncio.run(self.send(json.dumps({"progress": 25, "status": "progress"})))
        except Exception as e:
            return None

        i = 0
        for func in functions1 + functions2:
            function_text = func["full_text"]

            # Generate embeddings for function text
            text_embedding = generate_embedding(function_text)
            if text_embedding is None:
                print(f"Error generating embedding for function text: {function_text}")
                return None  # Terminate process immediately

            if i % 5 == 0:
                # Ping the frontend every 5 iterations
                try:
                    asyncio.run(
                        self.send(json.dumps({"ping": "ping"}))
                    )  # Send ping from the worker thread
                except Exception as e:
                    return None  # Stop the analysis if the connection is lost
            i += 1
            function_text_embeddings[function_text] = text_embedding

        # Notify progress after generating embeddings (60% progress)
        try:
            asyncio.run(self.send(json.dumps({"progress": 60, "status": "progress"})))
        except Exception as e:
            return None

        # Compare functions between the two repositories
        for func1 in functions1:
            for func2 in functions2:
                name_similarity = (
                    difflib.SequenceMatcher(
                        None, func1["signature"]["name"], func2["signature"]["name"]
                    ).ratio()
                    * 100
                )

                # Signature similarity using difflib
                signature1 = (
                    f"{func1['signature']['name']}({', '.join(func1['signature']['args'])})"
                )
                signature2 = (
                    f"{func2['signature']['name']}({', '.join(func2['signature']['args'])})"
                )

                signature_similarity = (
                    difflib.SequenceMatcher(None, signature1, signature2).ratio() * 100
                )

                # Content similarity using OpenAI embeddings
                fulltext1 = func1["full_text"]
                fulltext2 = func2["full_text"]

                content_similarity_openai = cosine_similarity(
                    function_text_embeddings[fulltext1], function_text_embeddings[fulltext2]
                )

                # Aggregate similarity
                overall_similarity = (
                    (name_similarity * 0.25)  # 25% for name similarity
                    + (signature_similarity * 0.25)  # 25% for signature similarity
                    + (content_similarity_openai * 0.5)  # 50% for content similarity
                )

                matching_details["functions"].append(
                    {
                        "name1": func1["signature"]["name"],
                        "name2": func2["signature"]["name"],
                        "name_similarity": round(name_similarity, 2),
                        "signature_similarity": round(signature_similarity, 2),
                        "content_similarity": round(content_similarity_openai, 2),
                        "similarity": round(overall_similarity, 2),
                    }
                )

        # Notify progress after extracting models (75% progress)
        try:
            asyncio.run(self.send(json.dumps({"progress": 75, "status": "progress"})))
        except Exception as e:
            return None

        # Compare Django models
        models1 = extract_django_models(repo1_path)
        models2 = extract_django_models(repo2_path)
        for model1 in models1:
            for model2 in models2:
                model_similarity = (
                    difflib.SequenceMatcher(None, model1["name"], model2["name"]).ratio() * 100
                )

                model_fields_similarity = compare_model_fields(model1, model2)
                matching_details["models"].append(
                    {
                        "name1": model1["name"],
                        "name2": model2["name"],
                        "similarity": round(model_similarity, 2),
                        "field_comparison": model_fields_similarity,
                    }
                )
        # Notify progress after completing all comparisons (100% progress)
        try:
            asyncio.run(self.send(json.dumps({"progress": 100, "status": "progress"})))
        except Exception as e:
            return None

        return matching_details
