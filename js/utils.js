// Utility functions for the user study

/**
 * Generate a unique user ID
 */
function generateUserId() {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return `user_${timestamp}_${random}`;
}

/**
 * Shuffle array using Fisher-Yates algorithm
 */
function shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

/**
 * Randomly sample n items from array
 */
function sampleArray(array, n) {
    const shuffled = shuffleArray(array);
    return shuffled.slice(0, n);
}

/**
 * Load JSON file
 */
async function loadJSON(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error loading JSON:', error);
        return null;
    }
}

/**
 * Load text file
 */
async function loadText(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Error loading text:', error);
        return null;
    }
}

/**
 * Parse mapping file into object
 */
function parseMappingText(text) {
    const mapping = {};
    const lines = text.split('\n');

    for (const line of lines) {
        if (line.trim() && !line.startsWith('#')) {
            const [index, filename] = line.split(':');
            if (index && filename) {
                mapping[parseInt(index)] = filename.trim();
            }
        }
    }

    return mapping;
}

/**
 * Format time duration
 */
function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

/**
 * Create video element with error handling
 */
function createVideoElement(src, options = {}) {
    const video = document.createElement('video');
    video.src = src;
    video.controls = options.controls !== false;
    video.preload = options.preload || 'metadata';

    if (options.width) video.width = options.width;
    if (options.height) video.height = options.height;

    video.addEventListener('error', function(e) {
        console.error('Video error:', e);
        console.error('Video source:', src);
    });

    return video;
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);
            return successful;
        } catch (err) {
            document.body.removeChild(textArea);
            return false;
        }
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: opacity 0.3s ease;
    `;

    // Set color based on type
    switch (type) {
        case 'success':
            notification.style.backgroundColor = '#10b981';
            break;
        case 'error':
            notification.style.backgroundColor = '#ef4444';
            break;
        case 'warning':
            notification.style.backgroundColor = '#f59e0b';
            break;
        default:
            notification.style.backgroundColor = '#3b82f6';
    }

    document.body.appendChild(notification);

    // Auto remove
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, duration);
}

/**
 * Validate form data
 */
function validateFormData(formData, requiredFields) {
    const missing = [];

    for (const field of requiredFields) {
        if (!formData.has(field) || !formData.get(field)) {
            missing.push(field);
        }
    }

    return {
        isValid: missing.length === 0,
        missingFields: missing
    };
}

/**
 * Get study data from localStorage
 */
function getStudyData() {
    const data = localStorage.getItem('userStudyData');
    return data ? JSON.parse(data) : null;
}

/**
 * Save study data to localStorage
 */
function saveStudyData(data) {
    localStorage.setItem('userStudyData', JSON.stringify(data));
}

/**
 * Clear study data from localStorage
 */
function clearStudyData() {
    localStorage.removeItem('userStudyData');
}