# services/bluesky_service.py
from atproto import Client, models
from django.conf import settings


class BlueSkyService:
    def __init__(self):
        self.client = Client()
        self.client.login(settings.BLUESKY_USERNAME, settings.BLUESKY_PASSWORD)

    def post_text(self, text):
        """Post plain text to BlueSky."""
        post = self.client.send_post(text=text)
        return post.uri  # Assuming the response includes a post ID

    def post_with_image(self, text, image_path):
        """Post text with an image to BlueSky."""
        try:
            # Read the image as binary
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()

            # Debug: Confirm image data size, not raw binary
            print(f"Uploading image to BlueSky... Size: {len(img_data)} bytes")

            # Upload the image to BlueSky
            upload = self.client.upload_blob(img_data)
            print(f"Upload response: Blob ID = {upload.blob}")

            # Create the embedded image structure
            images = [models.AppBskyEmbedImages.Image(alt="Activity Image", image=upload.blob)]
            embed = models.AppBskyEmbedImages.Main(images=images)
            print(f"Embed object: {embed}")

            # Create the post record
            post_record = models.AppBskyFeedPost.Record(
                text=text, embed=embed, created_at=self.client.get_current_time_iso()
            )

            # Post to BlueSky
            post = self.client.app.bsky.feed.post.create(self.client.me.did, post_record)
            print(f"Post created successfully. URI: {post.uri}")
            return post.uri
        except Exception as e:
            print(f"Error in post_with_image: {e}")
            raise

