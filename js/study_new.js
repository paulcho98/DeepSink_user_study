// Main study logic for comparison videos

class UserStudy {
    constructor() {
        this.studyConfig = null;
        this.currentComparisonSet = 0;
        this.currentVideoIndex = 0;
        this.currentVideos = [];
        this.responses = {};
        this.studyData = null;
        this.isInitialized = false;

        this.init();
    }

    async init() {
        try {
            // Check if user has valid study data
            this.studyData = getStudyData();
            if (!this.studyData) {
                window.location.href = 'index.html';
                return;
            }

            // Load configuration
            await this.loadConfiguration();

            // Initialize responses
            this.initializeResponses();

            // Setup UI
            this.setupUI();

            // Load first comparison set
            await this.loadComparisonSet();

            this.isInitialized = true;

        } catch (error) {
            console.error('Error initializing study:', error);
            this.showError(`Failed to initialize study: ${error.message}. Please refresh and try again.`);
        }
    }

    async loadConfiguration() {
        // Load study configuration
        this.studyConfig = await loadJSON('data/study_config.json');
        if (!this.studyConfig) {
            throw new Error('Failed to load study configuration');
        }
    }

    initializeResponses() {
        // Initialize responses for all comparison sets
        this.responses = {};
        this.studyConfig.comparison_sets.forEach(set => {
            this.responses[set.name] = {};
        });
    }

    async loadComparisonSet() {
        if (this.currentComparisonSet >= this.studyConfig.comparison_sets.length) {
            await this.showCompletion();
            return;
        }

        const comparisonSet = this.studyConfig.comparison_sets[this.currentComparisonSet];
        
        // Show loading state
        document.getElementById('loadingState').style.display = 'block';
        document.getElementById('studyInterface').style.display = 'none';

        // Load videos for this comparison set
        await this.loadVideosForComparison(comparisonSet);

        // Update UI
        this.updateProgress();
        this.currentVideoIndex = 0;
        
        // Load first video
        this.loadCurrentVideo();
    }

    async loadVideosForComparison(comparisonSet) {
        // Predefined video files based on the videos folder structure
        const videoFiles = [
            'easy_v2_017_comparison.mp4',
            'generated_027_comparison.mp4',
            'generated_032_comparison.mp4',
            'generated_037_comparison.mp4',
            'generated_038_comparison.mp4',
            'generated_054_comparison.mp4',
            'sampled_025_comparison.mp4',
            'sampled_027_comparison.mp4',
            'sampled_036_comparison.mp4',
            'sampled_038_comparison.mp4',
            'sampled_042_comparison.mp4',
            'sampled_049_comparison.mp4'
        ];
        
        this.currentVideos = videoFiles.map(file => ({
            filename: file,
            path: `${comparisonSet.video_folder}/${file}`,
            basename: file.replace('_comparison.mp4', '')
        }));
        
        // Shuffle videos for random order
        this.shuffleVideos();
    }

    shuffleVideos() {
        for (let i = this.currentVideos.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.currentVideos[i], this.currentVideos[j]] = [this.currentVideos[j], this.currentVideos[i]];
        }
    }

    loadCurrentVideo() {
        if (this.currentVideoIndex >= this.currentVideos.length) {
            // Move to next comparison set
            this.currentComparisonSet++;
            this.loadComparisonSet();
            return;
        }

        const video = this.currentVideos[this.currentVideoIndex];
        const comparisonSet = this.studyConfig.comparison_sets[this.currentComparisonSet];

        // Update UI elements
        document.getElementById('comparisonSetName').textContent = comparisonSet.display_name;
        document.getElementById('videoNumber').textContent = this.currentVideoIndex + 1;
        document.getElementById('totalVideosInSet').textContent = this.currentVideos.length;
        document.getElementById('currentVideoName').textContent = video.basename;

        // Load video
        const videoElement = document.getElementById('comparisonVideo');
        videoElement.src = video.path;
        
        // Reset form
        document.getElementById('choiceForm').reset();
        document.getElementById('submitChoice').disabled = true;

        // Load existing response if any
        this.loadExistingResponse();

        // Hide loading, show interface
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('studyInterface').style.display = 'block';

        // Update progress
        this.updateProgress();
    }

    loadExistingResponse() {
        const comparisonSet = this.studyConfig.comparison_sets[this.currentComparisonSet];
        const video = this.currentVideos[this.currentVideoIndex];
        const response = this.responses[comparisonSet.name][video.filename];

        if (response) {
            const radio = document.querySelector(`input[name="choice"][value="${response}"]`);
            if (radio) {
                radio.checked = true;
                document.getElementById('submitChoice').disabled = false;
            }
        }
    }

    setupUI() {
        // Update total comparison sets
        document.getElementById('totalComparisonSets').textContent = this.studyConfig.comparison_sets.length;

        // Setup choice form
        const choiceForm = document.getElementById('choiceForm');
        choiceForm.addEventListener('change', () => {
            document.getElementById('submitChoice').disabled = false;
        });

        choiceForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitChoice();
        });

        // Setup navigation buttons
        document.getElementById('prevVideo').addEventListener('click', () => {
            this.navigateVideo(-1);
        });

        document.getElementById('nextVideo').addEventListener('click', () => {
            this.navigateVideo(1);
        });

        // Setup video controls
        const video = document.getElementById('comparisonVideo');
        video.addEventListener('loadedmetadata', () => {
            document.getElementById('loadingText').style.display = 'none';
        });

        video.addEventListener('error', () => {
            this.showError('Failed to load video. Please try refreshing the page.');
        });
    }

    submitChoice() {
        const formData = new FormData(document.getElementById('choiceForm'));
        const choice = formData.get('choice');
        
        if (!choice) {
            alert('Please make a choice before submitting.');
            return;
        }

        // Save response
        const comparisonSet = this.studyConfig.comparison_sets[this.currentComparisonSet];
        const video = this.currentVideos[this.currentVideoIndex];
        this.responses[comparisonSet.name][video.filename] = choice;

        // Save to localStorage
        this.saveResponses();

        // Move to next video
        this.currentVideoIndex++;
        this.loadCurrentVideo();
    }

    navigateVideo(direction) {
        const newIndex = this.currentVideoIndex + direction;
        
        if (newIndex >= 0 && newIndex < this.currentVideos.length) {
            this.currentVideoIndex = newIndex;
            this.loadCurrentVideo();
        } else if (direction > 0 && newIndex >= this.currentVideos.length) {
            // Move to next comparison set
            this.currentComparisonSet++;
            this.loadComparisonSet();
        } else if (direction < 0 && this.currentComparisonSet > 0) {
            // Move to previous comparison set
            this.currentComparisonSet--;
            this.loadComparisonSet().then(() => {
                this.currentVideoIndex = this.currentVideos.length - 1;
                this.loadCurrentVideo();
            });
        }
    }

    updateProgress() {
        const totalVideos = this.studyConfig.comparison_sets.length * 10; // 10 videos per set
        const completedVideos = this.currentComparisonSet * 10 + this.currentVideoIndex;
        const progressPercent = (completedVideos / totalVideos) * 100;

        document.getElementById('currentProgress').textContent = completedVideos;
        document.getElementById('totalProgress').textContent = totalVideos;
        document.getElementById('progressBar').style.width = `${progressPercent}%`;
        
        // Update comparison set progress
        document.getElementById('currentComparisonSet').textContent = this.currentComparisonSet + 1;
    }

    saveResponses() {
        localStorage.setItem('userStudyResponses', JSON.stringify(this.responses));
        localStorage.setItem('userStudyProgress', JSON.stringify({
            currentComparisonSet: this.currentComparisonSet,
            currentVideoIndex: this.currentVideoIndex
        }));
    }

    loadResponses() {
        const saved = localStorage.getItem('userStudyResponses');
        if (saved) {
            this.responses = JSON.parse(saved);
        }

        const progress = localStorage.getItem('userStudyProgress');
        if (progress) {
            const progressData = JSON.parse(progress);
            this.currentComparisonSet = progressData.currentComparisonSet || 0;
            this.currentVideoIndex = progressData.currentVideoIndex || 0;
        }
    }

    async showCompletion() {
        // Generate final results
        const results = this.generateResults();
        
        // Save final results
        localStorage.setItem('userStudyFinalResults', JSON.stringify(results));

        // Show completion interface
        document.getElementById('studyInterface').style.display = 'none';
        document.getElementById('loadingState').style.display = 'none';
        
        const completionDiv = document.createElement('div');
        completionDiv.className = 'completion-screen';
        completionDiv.innerHTML = `
            <div class="completion-content">
                <h2>Study Completed!</h2>
                <p>Thank you for participating in our video generation comparison study.</p>
                <p>Your responses have been recorded.</p>
                <div class="completion-stats">
                    <p>Total comparisons completed: ${Object.keys(this.responses).length}</p>
                    <p>Total videos evaluated: ${Object.values(this.responses).reduce((sum, set) => sum + Object.keys(set).length, 0)}</p>
                </div>
                <button onclick="this.downloadResults()" class="download-btn">Download Results</button>
                <button onclick="window.location.href='index.html'" class="home-btn">Return to Home</button>
            </div>
        `;

        document.querySelector('.study-main').appendChild(completionDiv);
    }

    generateResults() {
        return {
            timestamp: new Date().toISOString(),
            participantId: this.studyData.participantId,
            demographics: this.studyData.demographics,
            responses: this.responses,
            studyDuration: Date.now() - this.studyData.startTime
        };
    }

    downloadResults() {
        const results = this.generateResults();
        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `user_study_results_${this.studyData.participantId}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <h3>Error</h3>
            <p>${message}</p>
            <button onclick="window.location.reload()">Refresh Page</button>
        `;

        document.querySelector('.study-main').innerHTML = '';
        document.querySelector('.study-main').appendChild(errorDiv);
    }
}

// Initialize study when page loads
document.addEventListener('DOMContentLoaded', () => {
    new UserStudy();
});