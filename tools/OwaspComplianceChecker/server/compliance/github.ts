import fetch from "node-fetch";

// Define GitHub file type interface
interface GitHubFile {
  name: string;
  path?: string;
  download_url?: string;
  type?: string;
  [key: string]: any;
}

// Function to fetch repository data from GitHub
export async function fetchRepositoryData(owner: string, repo: string) {
  try {
    // Set up default headers with user agent
    const headers = {
      'User-Agent': 'OWASP-Compliance-Checker',
      'Accept': 'application/vnd.github.v3+json'
    };
    
    // Fetch repository information
    const repoResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}`, { headers });
    
    if (!repoResponse.ok) {
      throw new Error(`Failed to fetch repository data: ${repoResponse.statusText}`);
    }
    
    const repoData = await repoResponse.json() as Record<string, any>;
    
    // Fetch repository contents (root directory)
    const contentsResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents`, { headers });
    
    if (!contentsResponse.ok) {
      throw new Error(`Failed to fetch repository contents: ${contentsResponse.statusText}`);
    }
    
    const contentsData = await contentsResponse.json() as GitHubFile[];
    
    // Fetch more directories that might contain useful files
    let allFiles: GitHubFile[] = [...contentsData];
    
    try {
      // Attempt to fetch docs directory if it exists
      const docsResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/docs`, { headers });
      if (docsResponse.ok) {
        const docsData = await docsResponse.json();
        if (Array.isArray(docsData)) {
          allFiles = [...allFiles, ...docsData.map(file => ({ ...file, path: `docs/${file.name}` }))];
        }
      }
    } catch (e) {
      // Docs directory might not exist, ignore error
    }
    
    try {
      // Check for .github directory which might contain workflow files
      const githubResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/.github`, { headers });
      if (githubResponse.ok) {
        const githubData = await githubResponse.json() as GitHubFile[];
        if (Array.isArray(githubData)) {
          allFiles = [...allFiles, ...githubData.map(file => ({ ...file, path: `.github/${file.name}` }))];
          
          // Check for workflows directory
          if (githubData.some(file => file.name === 'workflows' && file.type === 'dir')) {
            const workflowsResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/.github/workflows`, { headers });
            if (workflowsResponse.ok) {
              const workflowsData = await workflowsResponse.json() as GitHubFile[];
              if (Array.isArray(workflowsData)) {
                allFiles = [...allFiles, ...workflowsData.map(file => ({ ...file, path: `.github/workflows/${file.name}` }))];
              }
            }
          }
        }
      }
    } catch (e) {
      // .github directory might not exist, ignore error
    }

    // Check for package.json, requirements.txt, etc.
    const dependencyFiles = contentsData.filter(file => 
      ['package.json', 'requirements.txt', 'go.mod', 'composer.json', 'Gemfile'].includes(file.name)
    );
    
    let dependencies: Record<string, any> = {};
    
    // Parse package files for dependency information
    for (const depFile of dependencyFiles) {
      try {
        if (depFile.download_url) {
          const depResponse = await fetch(depFile.download_url, { headers });
          if (depResponse.ok) {
            const content = await depResponse.text();
            if (depFile.name === 'package.json') {
              const pkgJson = JSON.parse(content);
              dependencies = {
                ...dependencies,
                npm: {
                  dependencies: pkgJson.dependencies || {},
                  devDependencies: pkgJson.devDependencies || {}
                }
              };
            } else if (depFile.name === 'requirements.txt') {
              // Simple parsing for Python requirements
              const reqs = content.split('\n')
                .filter(line => line.trim() && !line.startsWith('#'))
                .map(line => line.split('==')[0].trim());
              dependencies = {
                ...dependencies,
                python: { dependencies: reqs }
              };
            }
            // Add more dependency file parsers as needed
          }
        }
      } catch (e) {
        console.error(`Error parsing dependency file ${depFile.name}:`, e);
      }
    }
    
    // Fetch readme content if it exists
    let readmeContent = "";
    const readmeFile = contentsData.find(file => 
      file.name.toUpperCase() === "README.MD" || file.name.toUpperCase() === "README"
    );
    
    if (readmeFile && readmeFile.download_url) {
      const readmeResponse = await fetch(readmeFile.download_url, { headers });
      if (readmeResponse.ok) {
        readmeContent = await readmeResponse.text();
      }
    }
    
    // Fetch CONTRIBUTING.md content if it exists
    let contributingContent = "";
    const contributingFile = contentsData.find(file => 
      file.name.toUpperCase() === "CONTRIBUTING.MD"
    );
    
    if (contributingFile && contributingFile.download_url) {
      const contributingResponse = await fetch(contributingFile.download_url, { headers });
      if (contributingResponse.ok) {
        contributingContent = await contributingResponse.text();
      }
    }
    
    // Fetch SECURITY.md content if it exists
    let securityContent = "";
    const securityFile = contentsData.find(file => 
      file.name.toUpperCase() === "SECURITY.MD"
    );
    
    if (securityFile && securityFile.download_url) {
      const securityResponse = await fetch(securityFile.download_url, { headers });
      if (securityResponse.ok) {
        securityContent = await securityResponse.text();
      }
    }
    
    // Fetch CHANGELOG.md content if it exists
    let changelogContent = "";
    const changelogFile = contentsData.find(file => 
      file.name.toUpperCase() === "CHANGELOG.MD"
    );
    
    if (changelogFile && changelogFile.download_url) {
      const changelogResponse = await fetch(changelogFile.download_url, { headers });
      if (changelogResponse.ok) {
        changelogContent = await changelogResponse.text();
      }
    }
    
    // Fetch pull requests
    const pullsResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/pulls?state=open&per_page=1`, { headers });
    let openPullRequestsCount = 0;
    let pullRequestsData: any[] = [];
    
    if (pullsResponse.ok) {
      const linkHeader = pullsResponse.headers.get('Link');
      if (linkHeader && linkHeader.includes('rel="last"')) {
        const match = linkHeader.match(/page=(\d+)>; rel="last"/);
        if (match) {
          openPullRequestsCount = parseInt(match[1], 10);
        }
      } else {
        pullRequestsData = await pullsResponse.json() as any[];
        openPullRequestsCount = pullRequestsData.length;
      }
    }
    
    // Fetch commits (for activity analysis)
    const commitsResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/commits?per_page=30`, { headers });
    let recentCommits: any[] = [];
    
    if (commitsResponse.ok) {
      recentCommits = await commitsResponse.json() as any[];
    }
    
    // Fetch releases
    const releasesResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/releases?per_page=5`, { headers });
    let releases: any[] = [];
    
    if (releasesResponse.ok) {
      releases = await releasesResponse.json() as any[];
    }
    
    // Fetch issues
    const issuesResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues?per_page=30&state=all`, { headers });
    let issues: any[] = [];
    
    if (issuesResponse.ok) {
      issues = await issuesResponse.json() as any[];
    }
    
    // Check for CI/CD and workflow files
    const hasGithubActions = allFiles.some(file => 
      file.path?.includes('.github/workflows') && 
      (file.name.endsWith('.yml') || file.name.endsWith('.yaml'))
    );
    
    const hasTravisConfig = allFiles.some(file => file.name === '.travis.yml');
    const hasJenkinsConfig = allFiles.some(file => file.name === 'Jenkinsfile');
    const hasCircleCIConfig = allFiles.some(file => file.name === '.circleci' || file.name === 'circle.yml');
    
    // Check for linting config files
    const hasEslintConfig = allFiles.some(file => 
      file.name === '.eslintrc' || 
      file.name === '.eslintrc.js' || 
      file.name === '.eslintrc.json' || 
      file.name === '.eslintrc.yml'
    );
    
    const hasPrettierConfig = allFiles.some(file => 
      file.name === '.prettierrc' || 
      file.name === '.prettierrc.js' || 
      file.name === '.prettierrc.json' || 
      file.name === '.prettierrc.yml'
    );
    
    const hasEditorConfig = allFiles.some(file => file.name === '.editorconfig');
    
    // Check for testing frameworks
    const hasTestDirectory = allFiles.some(file => 
      file.name === 'test' || 
      file.name === 'tests' || 
      file.name === '__tests__'
    );
    
    const hasJestConfig = allFiles.some(file => 
      file.name === 'jest.config.js' || 
      file.name === 'jest.config.json'
    );
    
    const hasMochaConfig = allFiles.some(file => file.name === '.mocharc.js' || file.name === '.mocharc.json');
    
    // Check for Docker and containerization
    const hasDockerfile = allFiles.some(file => file.name === 'Dockerfile');
    const hasDockerCompose = allFiles.some(file => file.name === 'docker-compose.yml' || file.name === 'docker-compose.yaml');
    
    // Combine all data
    return {
      ...repoData,
      files: allFiles,
      readme: readmeContent,
      contributing: contributingContent,
      security: securityContent,
      changelog: changelogContent,
      open_pull_requests_count: openPullRequestsCount,
      dependencies,
      recent_commits: recentCommits,
      releases,
      issues,
      
      // Simplified detection flags
      has_github_actions: hasGithubActions,
      has_travis: hasTravisConfig,
      has_jenkins: hasJenkinsConfig,
      has_circle_ci: hasCircleCIConfig,
      has_eslint: hasEslintConfig,
      has_prettier: hasPrettierConfig,
      has_editorconfig: hasEditorConfig,
      has_test_directory: hasTestDirectory,
      has_jest: hasJestConfig,
      has_mocha: hasMochaConfig,
      has_dockerfile: hasDockerfile,
      has_docker_compose: hasDockerCompose,
      
      // CI/CD flag
      has_ci_cd: hasGithubActions || hasTravisConfig || hasJenkinsConfig || hasCircleCIConfig,
      
      // Linting flag
      has_linting: hasEslintConfig || hasPrettierConfig || hasEditorConfig,
      
      // Testing flag
      has_testing: hasTestDirectory || hasJestConfig || hasMochaConfig
    };
  } catch (error) {
    console.error("Error fetching GitHub data:", error);
    throw error;
  }
}
