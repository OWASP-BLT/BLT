export const getSocialStats = async () => {
    // Fetch social stats from GitHub or another source
    const response = await fetch('https://api.github.com/repos/OWASP-BLT/BLT');
    const stats = await response.json();
    return {
        stars: stats.stargazers_count,
        forks: stats.forks_count,
        contributors: stats.contributors_count,
    };
};