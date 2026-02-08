/**
 * Timer Management JavaScript
 * Handles starting, stopping, pausing, and resuming timers
 */

class TimerManager {
    constructor() {
        this.activeTimer = null;
        this.timerInterval = null;
        this.apiBaseUrl = '/api/timelogs';
        this.init();
    }

    init() {
        this.loadActiveTimer();
        this.attachEventListeners();
    }

    attachEventListeners() {
        // Start timer button
        const startBtn = document.getElementById('start-timer-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startTimer());
        }

        // Stop timer button
        const stopBtn = document.getElementById('stop-timer-btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopTimer());
        }

        // Pause timer button
        const pauseBtn = document.getElementById('pause-timer-btn');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.pauseTimer());
        }

        // Resume timer button
        const resumeBtn = document.getElementById('resume-timer-btn');
        if (resumeBtn) {
            resumeBtn.addEventListener('click', () => this.resumeTimer());
        }
    }

    async loadActiveTimer() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/?end_time__isnull=true`, {
                headers: this.getHeaders()
            });

            if (response.ok) {
                const data = await response.json();
                if (data.results && data.results.length > 0) {
                    this.activeTimer = data.results[0];
                    this.updateUI();
                    this.startTimerDisplay();
                }
            }
        } catch (error) {
            console.error('Error loading active timer:', error);
        }
    }

    async startTimer() {
        const issueUrl = document.getElementById('github-issue-url')?.value;
        const issueNumber = document.getElementById('github-issue-number')?.value;
        const repo = document.getElementById('github-repo')?.value;

        const data = {};
        if (issueUrl) data.github_issue_url = issueUrl;
        if (issueNumber) data.github_issue_number = parseInt(issueNumber);
        if (repo) data.github_repo = repo;

        try {
            const response = await fetch(`${this.apiBaseUrl}/start/`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(data)
            });

            if (response.ok) {
                this.activeTimer = await response.json();
                this.updateUI();
                this.startTimerDisplay();
                this.showNotification('Timer started successfully', 'success');
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Failed to start timer', 'error');
            }
        } catch (error) {
            console.error('Error starting timer:', error);
            this.showNotification('Failed to start timer', 'error');
        }
    }

    async stopTimer() {
        if (!this.activeTimer) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/${this.activeTimer.id}/stop/`, {
                method: 'POST',
                headers: this.getHeaders()
            });

            if (response.ok) {
                const data = await response.json();
                this.showNotification(
                    `Timer stopped. Duration: ${this.formatDuration(data.duration)}`,
                    'success'
                );
                this.activeTimer = null;
                this.stopTimerDisplay();
                this.updateUI();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Failed to stop timer', 'error');
            }
        } catch (error) {
            console.error('Error stopping timer:', error);
            this.showNotification('Failed to stop timer', 'error');
        }
    }

    async pauseTimer() {
        if (!this.activeTimer) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/${this.activeTimer.id}/pause/`, {
                method: 'POST',
                headers: this.getHeaders()
            });

            if (response.ok) {
                this.activeTimer = await response.json();
                this.updateUI();
                this.showNotification('Timer paused', 'info');
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Failed to pause timer', 'error');
            }
        } catch (error) {
            console.error('Error pausing timer:', error);
            this.showNotification('Failed to pause timer', 'error');
        }
    }

    async resumeTimer() {
        if (!this.activeTimer) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/${this.activeTimer.id}/resume/`, {
                method: 'POST',
                headers: this.getHeaders()
            });

            if (response.ok) {
                this.activeTimer = await response.json();
                this.updateUI();
                this.showNotification('Timer resumed', 'success');
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Failed to resume timer', 'error');
            }
        } catch (error) {
            console.error('Error resuming timer:', error);
            this.showNotification('Failed to resume timer', 'error');
        }
    }

    startTimerDisplay() {
        this.stopTimerDisplay();
        this.timerInterval = setInterval(() => {
            this.updateTimerDisplay();
        }, 1000);
    }

    stopTimerDisplay() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    updateTimerDisplay() {
        if (!this.activeTimer) return;

        const display = document.getElementById('timer-display');
        if (!display) return;

        const startTime = new Date(this.activeTimer.start_time);
        const now = new Date();
        let elapsed = (now - startTime) / 1000; // seconds

        // Subtract paused duration
        if (this.activeTimer.paused_duration) {
            elapsed -= this.activeTimer.paused_duration;
        }

        // If currently paused, subtract current pause time
        if (this.activeTimer.is_paused && this.activeTimer.last_pause_time) {
            const pauseStart = new Date(this.activeTimer.last_pause_time);
            elapsed -= (now - pauseStart) / 1000;
        }

        display.textContent = this.formatSeconds(Math.max(0, elapsed));
    }

    updateUI() {
        const startBtn = document.getElementById('start-timer-btn');
        const stopBtn = document.getElementById('stop-timer-btn');
        const pauseBtn = document.getElementById('pause-timer-btn');
        const resumeBtn = document.getElementById('resume-timer-btn');
        const timerInfo = document.getElementById('timer-info');

        if (this.activeTimer) {
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-block';

            if (this.activeTimer.is_paused) {
                if (pauseBtn) pauseBtn.style.display = 'none';
                if (resumeBtn) resumeBtn.style.display = 'inline-block';
            } else {
                if (pauseBtn) pauseBtn.style.display = 'inline-block';
                if (resumeBtn) resumeBtn.style.display = 'none';
            }

            if (timerInfo) {
                let info = 'Timer running';
                if (this.activeTimer.github_issue_number) {
                    info += ` for issue #${this.activeTimer.github_issue_number}`;
                }
                if (this.activeTimer.is_paused) {
                    info += ' (PAUSED)';
                }
                timerInfo.textContent = info;
                timerInfo.style.display = 'block';
            }
        } else {
            if (startBtn) startBtn.style.display = 'inline-block';
            if (stopBtn) stopBtn.style.display = 'none';
            if (pauseBtn) pauseBtn.style.display = 'none';
            if (resumeBtn) resumeBtn.style.display = 'none';
            if (timerInfo) timerInfo.style.display = 'none';
        }
    }

    formatSeconds(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    formatDuration(durationStr) {
        // Parse Django DurationField format (e.g., "1:30:00")
        if (!durationStr) return '0:00:00';
        return durationStr;
    }

    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };

        // Add CSRF token if available
        const csrfToken = this.getCookie('csrftoken');
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        return headers;
    }

    getCookie(name) {
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

    showNotification(message, type = 'info') {
        // Simple notification - can be replaced with your notification system
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // If you have a notification element
        const notification = document.getElementById('timer-notification');
        if (notification) {
            notification.textContent = message;
            notification.className = `notification ${type}`;
            notification.style.display = 'block';
            
            setTimeout(() => {
                notification.style.display = 'none';
            }, 3000);
        }
    }
}

// Initialize timer manager when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.timerManager = new TimerManager();
    });
} else {
    window.timerManager = new TimerManager();
}
