document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('refresh-projects-btn').addEventListener('click', function() {
        fetch('/refresh-projects/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateProjects(data.projects);
            } else {
                alert('Failed to refresh projects. Please try again later.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again later.');
        });
    });

    function updateProjects(projects) {
        const projectList = document.querySelector('.project-list');
        projectList.innerHTML = '';

        projects.forEach(project => {
            const projectItem = document.createElement('li');
            projectItem.classList.add('project-item');

            const projectLink = document.createElement('a');
            projectLink.href = `/project/${project.slug}/`;
            projectLink.classList.add('project-link');

            if (project.logo_url) {
                const projectLogo = document.createElement('img');
                projectLogo.src = project.logo_url;
                projectLogo.alt = `${project.name} logo`;
                projectLogo.classList.add('project-logo');
                projectLogo.height = 100;
                projectLogo.width = 100;
                projectLink.appendChild(projectLogo);
            }

            const projectDetails = document.createElement('div');
            projectDetails.classList.add('project-details');

            const projectName = document.createElement('h3');
            projectName.textContent = project.name;
            projectDetails.appendChild(projectName);

            const projectDescription = document.createElement('p');
            projectDescription.textContent = project.description;
            projectDetails.appendChild(projectDescription);

            const projectLinks = document.createElement('div');
            projectLinks.classList.add('project-links');

            const githubLink = document.createElement('a');
            githubLink.href = project.github_url;
            githubLink.target = '_blank';
            githubLink.title = 'GitHub';
            githubLink.innerHTML = '<i class="fab fa-github"></i> GitHub';
            projectLinks.appendChild(githubLink);

            if (project.wiki_url) {
                const wikiLink = document.createElement('a');
                wikiLink.href = project.wiki_url;
                wikiLink.target = '_blank';
                wikiLink.title = 'Wiki';
                wikiLink.innerHTML = '<i class="fas fa-book"></i> Wiki';
                projectLinks.appendChild(wikiLink);
            }

            if (project.homepage_url) {
                const homepageLink = document.createElement('a');
                homepageLink.href = project.homepage_url;
                homepageLink.target = '_blank';
                homepageLink.title = 'Homepage';
                homepageLink.innerHTML = '<i class="fas fa-home"></i> Homepage';
                projectLinks.appendChild(homepageLink);
            }

            projectDetails.appendChild(projectLinks);

            const projectStats = document.createElement('div');
            projectStats.classList.add('project-stats');

            const topContributors = document.createElement('p');
            topContributors.textContent = 'Top Contributors:';
            projectStats.appendChild(topContributors);

            const contributors = document.createElement('div');
            contributors.classList.add('contributors');

            project.get_top_contributors.forEach(contributor => {
                const contributorAvatar = document.createElement('img');
                contributorAvatar.src = contributor.avatar_url;
                contributorAvatar.alt = contributor.name;
                contributorAvatar.classList.add('contributor-avatar');
                contributorAvatar.title = contributor.name;
                contributorAvatar.height = 40;
                contributorAvatar.width = 40;
                contributors.appendChild(contributorAvatar);
            });

            projectStats.appendChild(contributors);
            projectDetails.appendChild(projectStats);

            const additionalMetadata = document.createElement('div');
            additionalMetadata.classList.add('additional-metadata');

            const freshness = document.createElement('p');
            freshness.textContent = `Freshness: ${project.freshness}`;
            additionalMetadata.appendChild(freshness);

            const stars = document.createElement('p');
            stars.textContent = `Stars: ${project.stars}`;
            additionalMetadata.appendChild(stars);

            const forks = document.createElement('p');
            forks.textContent = `Forks: ${project.forks}`;
            additionalMetadata.appendChild(forks);

            const externalLinks = document.createElement('div');
            externalLinks.classList.add('external-links');

            const externalLinksTitle = document.createElement('h4');
            externalLinksTitle.textContent = 'External Links';
            externalLinks.appendChild(externalLinksTitle);

            const externalLinksList = document.createElement('ul');

            project.external_links.forEach(link => {
                const externalLinkItem = document.createElement('li');
                const externalLink = document.createElement('a');
                externalLink.href = link.url;
                externalLink.target = '_blank';
                externalLink.textContent = link.name;
                externalLinkItem.appendChild(externalLink);
                externalLinksList.appendChild(externalLinkItem);
            });

            externalLinks.appendChild(externalLinksList);
            additionalMetadata.appendChild(externalLinks);
            projectDetails.appendChild(additionalMetadata);

            const projectTags = document.createElement('div');
            projectTags.classList.add('project-tags');

            const tagsTitle = document.createElement('h4');
            tagsTitle.textContent = 'Tags';
            projectTags.appendChild(tagsTitle);

            const tagsList = document.createElement('ul');

            project.tags.forEach(tag => {
                const tagItem = document.createElement('li');
                tagItem.textContent = tag.name;
                tagsList.appendChild(tagItem);
            });

            projectTags.appendChild(tagsList);
            projectDetails.appendChild(projectTags);

            projectLink.appendChild(projectDetails);
            projectItem.appendChild(projectLink);
            projectList.appendChild(projectItem);
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
