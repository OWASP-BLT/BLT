import fs from 'fs';
import { Octokit } from "@octokit/rest";
import { WebClient } from "@slack/web-api";

async function run() {
    try {
        // Read GitHub context from the JSON file
        const githubContextPath = process.argv[2];
        if (!githubContextPath || !fs.existsSync(githubContextPath)) {
            console.error('GitHub context file missing or not provided');
            process.exit(1);
        }

        const contextData = fs.readFileSync(githubContextPath, 'utf8');
        const context = JSON.parse(contextData);

        console.log('Parsed GitHub Context:', context);

        const event = context.event || {};
        const comment = event.comment || {};
        const issue = event.issue || {};
        const repository = event.repository || {};

        if (!comment.body || !issue.number || !repository.full_name) {
            console.error('Missing required GitHub context data');
            process.exit(1);
        }

        // Bounty command regex
        const bountyRegex = /\/bounty\s+\$(\d+)/;
        const match = comment.body.match(bountyRegex);

        if (!match) {
            console.log('No bounty command found');
            return;
        }

        const bountyAmount = parseInt(match[1], 10);
        const [repoOwner, repoName] = repository.full_name.split('/');
        const issueNumber = issue.number;
        const commenter = comment.user?.login || 'Unknown';

        const github = new Octokit({ auth: process.env.PERSONAL_ACCESS_TOKEN });
        const slack = new WebClient(process.env.SLACK_BOT_TOKEN);

        // Retrieve existing labels
        const { data: labels } = await github.issues.listLabelsOnIssue({
            owner: repoOwner,
            repo: repoName,
            issue_number: issueNumber,
        });

        let totalBounty = bountyAmount;
        const bountyLabelPrefix = "$";
        const bountyLabel = labels.find((label) => label.name.startsWith(bountyLabelPrefix));

        if (bountyLabel) {
            const existingBounty = parseInt(bountyLabel.name.slice(1), 10);
            totalBounty += existingBounty;
        }

        const newBountyLabel = `${bountyLabelPrefix}${totalBounty}`;

        try {
            if (bountyLabel) {
                await github.issues.updateLabel({
                    owner: repoOwner,
                    repo: repoName,
                    name: bountyLabel.name,
                    new_name: newBountyLabel,
                });
            } else {
                await github.issues.addLabels({
                    owner: repoOwner,
                    repo: repoName,
                    issue_number: issueNumber,
                    labels: [newBountyLabel],
                });
            }
        } catch (labelError) {
            console.error('Label Update Error:', labelError);
        }

        // Track the number of developers the user has sponsored
        const sponsorshipHistory = {};
        if (!sponsorshipHistory[commenter]) {
            sponsorshipHistory[commenter] = 1;
        } else {
            sponsorshipHistory[commenter] += 1;
        }

        // Find existing bounty comment
        const { data: comments } = await github.issues.listComments({
            owner: repoOwner,
            repo: repoName,
            issue_number: issueNumber,
        });

        const bountyComment = comments.find((c) => c.body.includes("💰 A bounty has been added!"));

        const commentBody = `💰 A bounty has been added!\n\nThis issue now has a total bounty of **$${totalBounty}** thanks to @${commenter}.\nThey have sponsored **${sponsorshipHistory[commenter]}** developers so far!\n\nWant to contribute? Solve this issue and claim the reward.`;

        try {
            if (bountyComment) {
                await github.issues.updateComment({
                    owner: repoOwner,
                    repo: repoName,
                    comment_id: bountyComment.id,
                    body: commentBody,
                });
            } else {
                await github.issues.createComment({
                    owner: repoOwner,
                    repo: repoName,
                    issue_number: issueNumber,
                    body: commentBody,
                });
            }
        } catch (commentError) {
            console.error('Comment Creation Error:', commentError);
        }

        try {
            await slack.chat.postMessage({
                channel: '#bounty-alerts',
                text: `🚀 *Bounty Alert!*\n@${commenter} has added a *$${bountyAmount}* bounty to <https://github.com/${repository.full_name}/issues/${issueNumber}|#${issueNumber}>.\nThe total bounty for this issue is now *$${totalBounty}*.\nContribute now and earn rewards!`
            });
        } catch (slackError) {
            console.error('Slack Notification Error:', slackError);
        }

        console.log(`Bounty processed: $${bountyAmount} added by ${commenter}`);
    } catch (error) {
        console.error('Bounty Bot Unexpected Error:', error);
        process.exit(1);
    }
}

run();
