// Main study logic for comparison videos

class UserStudy {
    constructor() {
        this.studyConfig = null;
        this.promptTexts = null;
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

        // Load prompt texts
        this.promptTexts = await loadJSON('prompt_text.json');
        if (!this.promptTexts) {
            console.warn('Failed to load prompt texts - prompts will not be displayed');
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
        const loadingState = document.getElementById('loadingState');
        const studyInterface = document.getElementById('studyInterface');
        
        if (loadingState) loadingState.style.display = 'block';
        if (studyInterface) studyInterface.style.display = 'none';

        // Load videos for this comparison set
        await this.loadVideosForComparison(comparisonSet);

        // Update UI
        this.updateProgress();
        this.currentVideoIndex = 0;
        
        // Load first video
        this.loadCurrentVideo();
    }

    async loadVideosForComparison(comparisonSet) {
        // Get existing videos for this comparison set
        const existingVideos = this.getExistingVideos(comparisonSet.video_folder);
        
        // Separate videos by duration (30s vs 60s)
        const videos30s = existingVideos.filter(v => v.filename.startsWith('30s_'));
        const videos60s = existingVideos.filter(v => v.filename.startsWith('60s_'));
        
        // Randomly select 4 videos: 2 from 30s and 2 from 60s
        const shuffled30s = this.shuffleArray([...videos30s]);
        const shuffled60s = this.shuffleArray([...videos60s]);
        
        // Select 2 from each duration
        const selectedFiles = [
            ...shuffled30s.slice(0, 2),
            ...shuffled60s.slice(0, 2)
        ];
        
        // Shuffle the final selection to randomize order
        const shuffledSelection = this.shuffleArray(selectedFiles);
        
        this.currentVideos = shuffledSelection.map(video => ({
            filename: video.filename,
            path: `${comparisonSet.video_folder}/${video.filename}`,
            basename: video.basename
        }));
    }

    shuffleArray(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
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
        
        // Display prompt text
        const currentPromptTextEl = document.getElementById('currentPromptText');
        if (currentPromptTextEl && this.promptTexts) {
            const promptText = this.promptTexts[video.basename];
            if (promptText) {
                currentPromptTextEl.textContent = promptText;
            } else {
                currentPromptTextEl.textContent = 'Prompt not available for this video.';
            }
        } else if (currentPromptTextEl) {
            currentPromptTextEl.textContent = 'Loading prompt...';
        }

        // Load video
        const videoElement = document.getElementById('comparisonVideo');
        if (videoElement) {
            console.log('Loading video:', video.path);
            
            // Clear any previous error states
            videoElement.classList.remove('video-error');
            
            // Configure video for seeking BEFORE setting source
            videoElement.controls = true; // Enable controls (including timeline)
            videoElement.muted = true; // Muted for autoplay compatibility
            videoElement.preload = 'auto'; // Preload video data for seeking
            videoElement.autoplay = false; // Don't autoplay - let user control playback
            
            // Make video focusable for keyboard controls
            videoElement.setAttribute('tabindex', '0');
            
            // Set video source
            videoElement.src = video.path;
            
            // Force video to load
            videoElement.load();
            
            // Focus video element so keyboard controls work
            setTimeout(() => {
                videoElement.focus();
            }, 100);
            
            // Add better error handling
            videoElement.onerror = (e) => {
                console.error('Video loading error details:', {
                    error: e,
                    src: videoElement.src,
                    networkState: videoElement.networkState,
                    readyState: videoElement.readyState,
                    currentTime: videoElement.currentTime,
                    duration: videoElement.duration
                });
                
                // Mark video as error state
                videoElement.classList.add('video-error');
                
                // Try to verify if file exists by making a HEAD request
                this.verifyVideoFile(video.path);
            };
            
            videoElement.onloadstart = () => {
                console.log('비디오 로딩 시작:', video.path);
            };
            
            videoElement.oncanplay = () => {
                console.log('비디오 재생 준비 완료:', video.path);
                videoElement.classList.remove('video-error');
            };
            
            videoElement.onloadedmetadata = () => {
                console.log('비디오 메타데이터 로드됨:', {
                    src: video.path,
                    duration: videoElement.duration,
                    videoWidth: videoElement.videoWidth,
                    videoHeight: videoElement.videoHeight
                });
            };
            
            // Ensure video is seekable once enough data is loaded
            videoElement.oncanplaythrough = () => {
                console.log('비디오 전체 재생 가능 (seeking enabled):', video.path);
                videoElement.controls = true;
                // Ensure seeking is enabled
                if (videoElement.seekable.length > 0) {
                    console.log('Video is seekable, range:', videoElement.seekable.start(0), 'to', videoElement.seekable.end(0));
                }
            };
            
            // Enable seeking as soon as we have some data
            videoElement.onloadeddata = () => {
                console.log('Video data loaded, enabling seeking');
                videoElement.controls = true;
            };
            
            videoElement.onprogress = () => {
                if (videoElement.buffered.length > 0 && videoElement.seekable.length > 0) {
                    // Video has buffered and seekable data
                    videoElement.controls = true;
                    console.log('Video buffered, seeking should work');
                }
            };
            
            // Ensure video controls are always enabled and interactive
            videoElement.onloadedmetadata = () => {
                videoElement.controls = true;
                // Ensure the video can be controlled
                if (videoElement.seekable.length > 0) {
                    console.log('Video metadata loaded, seeking range:', 
                        videoElement.seekable.start(0), 'to', videoElement.seekable.end(0));
                }
            };
            
            // Add explicit keyboard event handlers for seeking
            videoElement.addEventListener('keydown', (e) => {
                // Don't prevent default - let browser handle video controls
                // But ensure video is focused
                if (e.target !== videoElement) {
                    videoElement.focus();
                }
            });
            
            // Ensure clicking on video focuses it
            videoElement.addEventListener('click', () => {
                videoElement.focus();
            });
        }
        
        // Reset form
        const choiceForm = document.getElementById('choiceForm');
        if (choiceForm) {
            choiceForm.reset();
        }
        
        const submitChoice = document.getElementById('submitChoice');
        if (submitChoice) {
            submitChoice.disabled = true;
        }

        // Load existing response if any
        this.loadExistingResponse();

        // Hide loading, show interface
        const loadingState = document.getElementById('loadingState');
        if (loadingState) loadingState.style.display = 'none';
        
        const studyInterface = document.getElementById('studyInterface');
        if (studyInterface) studyInterface.style.display = 'block';

        // Update progress
        this.updateProgress();
    }

    loadExistingResponse() {
        const comparisonSet = this.studyConfig.comparison_sets[this.currentComparisonSet];
        const video = this.currentVideos[this.currentVideoIndex];
        const response = this.responses[comparisonSet.name][video.filename];

        if (response && response.answers) {
            // Load answers for new multi-question format
            for (const [questionName, answer] of Object.entries(response.answers)) {
                const radio = document.querySelector(`input[name="${questionName}"][value="${answer}"]`);
                if (radio) {
                    radio.checked = true;
                }
            }
            this.checkAllQuestionsAnswered();
        } else if (typeof response === 'string') {
            // Legacy format compatibility - convert single choice to overall_quality
            const radio = document.querySelector(`input[name="overall_quality"][value="${response}"]`);
            if (radio) {
                radio.checked = true;
                this.checkAllQuestionsAnswered();
            }
        }
    }

    setupUI() {

        // Setup choice form
        const choiceForm = document.getElementById('choiceForm');
        if (choiceForm) {
            choiceForm.addEventListener('change', () => {
                this.checkAllQuestionsAnswered();
            });

            choiceForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitChoice();
            });
        }

        // Setup navigation buttons
        const prevVideo = document.getElementById('prevVideo');
        if (prevVideo) {
            prevVideo.addEventListener('click', () => {
                this.navigateVideo(-1);
            });
        }

        const nextVideo = document.getElementById('nextVideo');
        if (nextVideo) {
            nextVideo.addEventListener('click', () => {
                this.navigateVideo(1);
            });
        }

        // Setup video controls
        const video = document.getElementById('comparisonVideo');
        if (video) {
            // Basic video event logging (detailed error handling is now in loadCurrentVideo)
            video.addEventListener('loadstart', () => {
                console.log('비디오 로딩 시작됨:', video.src);
            });

            video.addEventListener('canplay', () => {
                console.log('비디오 재생 가능:', video.src);
            });
        }
    }

    checkAllQuestionsAnswered() {
        const questionNames = [
            'color_consistency',
            'dynamic_motion', 
            'subject_consistency',
            'overall_quality'
        ];
        
        let allAnswered = true;
        for (const questionName of questionNames) {
            const answered = document.querySelector(`input[name="${questionName}"]:checked`);
            if (!answered) {
                allAnswered = false;
                break;
            }
        }
        
        const submitChoice = document.getElementById('submitChoice');
        if (submitChoice) submitChoice.disabled = !allAnswered;
    }

    async verifyVideoFile(videoPath) {
        try {
            console.log('비디오 파일 존재 확인 중:', videoPath);
            
            const response = await fetch(videoPath, { method: 'HEAD' });
            
            if (response.ok) {
                const contentType = response.headers.get('content-type');
                const contentLength = response.headers.get('content-length');
                
                console.log('비디오 파일 정보:', {
                    path: videoPath,
                    status: response.status,
                    contentType: contentType,
                    contentLength: contentLength,
                    size: contentLength ? `${(contentLength / 1024 / 1024).toFixed(2)} MB` : 'Unknown'
                });
                
                if (!contentType || !contentType.startsWith('video/')) {
                    this.showError(`파일이 올바른 비디오 형식이 아닙니다: ${videoPath}`);
                } else {
                    this.showError(`비디오 파일은 존재하지만 로드할 수 없습니다: ${videoPath}. 브라우저 호환성 문제일 수 있습니다.`);
                }
            } else {
                console.error('비디오 파일이 존재하지 않습니다:', {
                    path: videoPath,
                    status: response.status,
                    statusText: response.statusText
                });
                
                this.showError(`비디오 파일을 찾을 수 없습니다: ${videoPath} (HTTP ${response.status})`);
            }
        } catch (error) {
            console.error('비디오 파일 확인 중 오류:', error);
            this.showError(`네트워크 오류로 인해 비디오 파일을 확인할 수 없습니다: ${videoPath}`);
        }
    }

    submitChoice() {
        const choiceForm = document.getElementById('choiceForm');
        if (!choiceForm) {
            this.showError('Form not found. Please refresh the page.');
            return;
        }
        
        const formData = new FormData(choiceForm);
        
        // Collect all answers
        const questionNames = [
            'color_consistency',
            'dynamic_motion', 
            'subject_consistency',
            'overall_quality'
        ];
        
        const answers = {};
        let allAnswered = true;
        
        for (const questionName of questionNames) {
            const answer = formData.get(questionName);
            if (!answer) {
                allAnswered = false;
                break;
            }
            answers[questionName] = answer;
        }
        
        if (!allAnswered) {
            alert('Please answer all questions before submitting.');
            return;
        }

        // Save responses
        const comparisonSet = this.studyConfig.comparison_sets[this.currentComparisonSet];
        const video = this.currentVideos[this.currentVideoIndex];
        this.responses[comparisonSet.name][video.filename] = {
            answers: answers,
            timestamp: new Date().toISOString()
        };

        // Save to localStorage
        this.saveResponses();

        // Move to next video
        this.currentVideoIndex++;
        this.loadCurrentVideo();
    }

    async navigateVideo(direction) {
        const newIndex = this.currentVideoIndex + direction;
        
        if (newIndex >= 0 && newIndex < this.currentVideos.length) {
            this.currentVideoIndex = newIndex;
            this.loadCurrentVideo();
        } else if (direction > 0 && newIndex >= this.currentVideos.length) {
            // Move to next comparison set
            this.currentComparisonSet++;
            this.currentVideoIndex = 0;
            await this.loadComparisonSet();
        } else if (direction < 0 && this.currentComparisonSet > 0) {
            // Move to previous comparison set
            this.currentComparisonSet--;
            this.currentVideoIndex = 3; // Last video in previous set (now 4 videos per set)
            await this.loadComparisonSet();
        }
    }

    updateProgress() {
        const totalVideos = this.studyConfig.comparison_sets.length * 4; // 4 videos per set = 16 total
        const completedVideos = this.currentComparisonSet * 4 + this.currentVideoIndex;
        const progressPercent = (completedVideos / totalVideos) * 100;

        const currentProgressEl = document.getElementById('currentProgress');
        if (currentProgressEl) currentProgressEl.textContent = completedVideos;
        
        const totalProgressEl = document.getElementById('totalProgress');
        if (totalProgressEl) totalProgressEl.textContent = totalVideos;
        
        const progressBar = document.getElementById('progressBar');
        if (progressBar) progressBar.style.width = `${progressPercent}%`;
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

        // Show loading message
        const loadingState = document.getElementById('loadingState');
        const studyInterface = document.getElementById('studyInterface');
        
        if (loadingState) {
            loadingState.style.display = 'block';
            const loadingText = document.getElementById('loadingText');
            if (loadingText) loadingText.textContent = 'Submitting your results...';
        }
        if (studyInterface) studyInterface.style.display = 'none';

        // Try to submit results to GitHub
        try {
            await this.submitResultsToGitHub(results);
            this.showSuccessCompletion(results);
        } catch (error) {
            console.error('Failed to submit results:', error);
            this.showManualCompletion(results);
        }
    }

    async submitResultsToGitHub(results) {
        // Use Vercel serverless function to submit results securely
        // The GitHub token is stored server-side and never exposed to the client
        
        // Determine API endpoint based on environment
        // For Vercel: use /api/submit-results
        // For local development: use http://localhost:3000/api/submit-results (if running Vercel dev)
        // Fallback: try relative path first (works on Vercel)
        const apiEndpoint = '/api/submit-results';
        
        try {
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(results)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `Server error: ${response.status}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            // If API endpoint doesn't exist (e.g., local development without serverless function),
            // fall back to showing manual submission
            console.error('Failed to submit via API:', error);
            throw error;
        }
    }

    showSuccessCompletion(results) {
        // Hide loading, show success completion
        const loadingState = document.getElementById('loadingState');
        if (loadingState) loadingState.style.display = 'none';
        
        const completionDiv = document.createElement('div');
        completionDiv.className = 'completion-screen';
        completionDiv.innerHTML = `
            <div class="completion-content">
                <h2>✅ Study Completed Successfully!</h2>
                <p>Thank you for participating in our video generation comparison study.</p>
                <p><strong>Your results have been automatically submitted as a GitHub issue.</strong></p>
                <div class="completion-stats">
                    <p>Total comparison sets completed: ${Object.keys(this.responses).length}</p>
                    <p>Total videos evaluated: ${Object.values(this.responses).reduce((sum, set) => sum + Object.keys(set).length, 0)}</p>
                    <p>Study duration: ${Math.round((Date.now() - this.studyData.startTime) / 1000 / 60)} minutes</p>
                </div>
                <p class="thank-you">Your contribution helps advance video generation research. Thank you!</p>
                <div class="completion-buttons">
                    <button onclick="userStudy.downloadResults()" class="download-btn">📋 Download Results (Backup)</button>
                    <button onclick="window.location.href='index.html'" class="home-btn">🏠 Return to Home</button>
                </div>
            </div>
        `;

        document.querySelector('.study-main').appendChild(completionDiv);
    }

    showManualCompletion(results) {
        // Hide loading, show manual completion
        const loadingState = document.getElementById('loadingState');
        if (loadingState) loadingState.style.display = 'none';
        
        const completionDiv = document.createElement('div');
        completionDiv.className = 'completion-screen';
        completionDiv.innerHTML = `
            <div class="completion-content">
                <h2>⚠️ Manual Submission Required</h2>
                <p>Thank you for participating in our video generation comparison study.</p>
                <p><strong>Automatic submission failed. Please help us by copying the results below and sending them to the researchers.</strong></p>
                <div class="completion-stats">
                    <p>Total comparison sets completed: ${Object.keys(this.responses).length}</p>
                    <p>Total videos evaluated: ${Object.values(this.responses).reduce((sum, set) => sum + Object.keys(set).length, 0)}</p>
                    <p>Study duration: ${Math.round((Date.now() - this.studyData.startTime) / 1000 / 60)} minutes</p>
                </div>
                <div class="results-section">
                    <h3>📋 Results Data (Please copy and send to researchers):</h3>
                    <textarea id="resultsTextarea" readonly class="results-textarea">${JSON.stringify(results, null, 2)}</textarea>
                    <button onclick="userStudy.copyResults()" class="copy-btn">📋 Copy Results</button>
                </div>
                <div class="completion-buttons">
                    <button onclick="userStudy.downloadResults()" class="download-btn">💾 Download Results</button>
                    <button onclick="window.location.href='index.html'" class="home-btn">🏠 Return to Home</button>
                </div>
            </div>
        `;

        document.querySelector('.study-main').appendChild(completionDiv);
    }

    copyResults() {
        const textarea = document.getElementById('resultsTextarea');
        if (textarea) {
            textarea.select();
            document.execCommand('copy');
            alert('Results copied to clipboard!');
        }
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

    getExistingVideos(videoFolder) {
        const folderName = videoFolder.split('/').pop();
        
        // Only include files that actually exist in each folder
        const actualFiles = {
            'deepsink_vs_self_forcing': [
                '30s_109_comparison.mp4',
                '30s_24_comparison.mp4',
                '30s_2_comparison.mp4',
                '30s_32_comparison.mp4',
                '30s_42_comparison.mp4',
                '30s_43_comparison.mp4',
                '30s_46_comparison.mp4',
                '30s_47_comparison.mp4',
                '30s_4_comparison.mp4',
                '30s_69_comparison.mp4',
                '30s_74_comparison.mp4',
                '30s_7_comparison.mp4',
                '30s_88_comparison.mp4',
                '60s_28_comparison.mp4',
                '60s_2_comparison.mp4',
                '60s_43_comparison.mp4',
                '60s_46_comparison.mp4',
                '60s_47_comparison.mp4',
                '60s_53_comparison.mp4',
                '60s_70_comparison.mp4'
            ],
            'deepsink_vs_long_live': [
                '30s_109_comparison.mp4',
                '30s_24_comparison.mp4',
                '30s_2_comparison.mp4',
                '30s_32_comparison.mp4',
                '30s_42_comparison.mp4',
                '30s_43_comparison.mp4',
                '30s_46_comparison.mp4',
                '30s_47_comparison.mp4',
                '30s_4_comparison.mp4',
                '30s_69_comparison.mp4',
                '30s_74_comparison.mp4',
                '30s_7_comparison.mp4',
                '30s_88_comparison.mp4',
                '60s_28_comparison.mp4',
                '60s_2_comparison.mp4',
                '60s_43_comparison.mp4',
                '60s_46_comparison.mp4',
                '60s_47_comparison.mp4',
                '60s_53_comparison.mp4',
                '60s_70_comparison.mp4'
            ],
            'deepsink_vs_causvid': [
                '30s_109_comparison.mp4',
                '30s_24_comparison.mp4',
                '30s_2_comparison.mp4',
                '30s_32_comparison.mp4',
                '30s_42_comparison.mp4',
                '30s_43_comparison.mp4',
                '30s_46_comparison.mp4',
                '30s_47_comparison.mp4',
                '30s_4_comparison.mp4',
                '30s_69_comparison.mp4',
                '30s_74_comparison.mp4',
                '30s_7_comparison.mp4',
                '30s_88_comparison.mp4',
                '60s_28_comparison.mp4',
                '60s_2_comparison.mp4',
                '60s_43_comparison.mp4',
                '60s_46_comparison.mp4',
                '60s_47_comparison.mp4',
                '60s_53_comparison.mp4',
                '60s_70_comparison.mp4'
            ],
            'deepsink_vs_rolling_forcing': [
                '30s_109_comparison.mp4',
                '30s_24_comparison.mp4',
                '30s_2_comparison.mp4',
                '30s_32_comparison.mp4',
                '30s_42_comparison.mp4',
                '30s_43_comparison.mp4',
                '30s_46_comparison.mp4',
                '30s_47_comparison.mp4',
                '30s_4_comparison.mp4',
                '30s_69_comparison.mp4',
                '30s_74_comparison.mp4',
                '30s_7_comparison.mp4',
                '30s_88_comparison.mp4',
                '60s_28_comparison.mp4',
                '60s_2_comparison.mp4',
                '60s_43_comparison.mp4',
                '60s_46_comparison.mp4',
                '60s_47_comparison.mp4',
                '60s_53_comparison.mp4',
                '60s_70_comparison.mp4'
            ]
        };
        
        const files = actualFiles[folderName] || [];
        return files.map(filename => ({
            filename: filename,
            basename: filename.replace('_comparison.mp4', '')
        }));
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