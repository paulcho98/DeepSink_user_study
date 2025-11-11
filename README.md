# Audio-Visual User Study Website

This directory contains a complete user study website for evaluating audio-driven facial animation models.

## 📁 Structure

```
user_study_comparisons/
├── index.html                 # Landing page with instructions
├── study.html                 # Main study interface
├── css/style.css             # Styling
├── js/
│   ├── study.js              # Main study logic
│   └── utils.js              # Utility functions
├── data/
│   ├── study_config.json     # Study configuration
│   ├── hallo3_avspeech_mapping.txt
│   ├── hunyuan_avspeech_mapping.txt
│   └── omniavatar_avspeech_mapping.txt
└── [comparison video folders]/
    ├── hallo3_NEW_avspeech_OG_vs_la_1/
    ├── hunyuan_NEW_avspeech_AR_vs_la_margin3/
    └── omniavatar_NEW_avspeech_OG_vs_la/
```

## 🎯 Study Design

- **Methods**: 3 models (Hallo3, Hunyuan, OmniAvatar)
- **Dataset**: AVSpeech only
- **Videos**: 3 random samples per method = 9 total comparisons
- **Questions**: 4 per video comparison
- **Blind Test**: Model A/B randomized, order tracked in order_sheet.txt files

## 📋 Questions

1. **[Character Consistency]** Which model shows better character consistency?
2. **[Overall Quality]** Which model shows better overall quality results?
3. **[Expression Realism]** Which model shows more natural and realistic expressions?
4. **[Lip Sync Performance]** Which model shows better lip sync performance?

## 🔢 Result Encoding

Format: `method-dataset-videoIndex-answers`

Example: `1-1-15-2134`
- Method: 1 (Hunyuan, 0=Hallo3, 1=Hunyuan, 2=OmniAvatar)
- Dataset: 1 (AVSpeech)
- Video Index: 15
- Answers: 2134 (Question 1=Model B, Question 2=Model A, Question 3=Model B, Question 4=Model B)

## 🚀 Deployment

For GitHub Pages deployment:

1. Copy this entire directory to your repository
2. Enable GitHub Pages in repository settings
3. Set source to the branch containing this directory
4. The website will be available at `https://username.github.io/repository/user_study_comparisons/`

## 🔧 Local Testing

```bash
# Simple HTTP server (Python)
python -m http.server 8000

# Or using Node.js
npx serve .

# Then visit http://localhost:8000
```

## 📊 Data Collection

Users will receive a result code at the end that looks like:
```
0-1-3-1221
0-1-17-2112
1-1-8-1122
...
```

Use the corresponding `order_sheet.txt` files to decode which model was actually A/B for each video.

## ⚙️ Features

- **Responsive Design**: Works on desktop and mobile
- **Progress Tracking**: Visual progress bar and completion status
- **Local Storage**: Preserves progress if page is refreshed
- **Error Handling**: Graceful handling of missing videos or network issues
- **Accessibility**: Keyboard navigation and screen reader friendly
- **Copy to Clipboard**: Easy result code copying for users

## 🎬 Video Format

Each comparison video shows three parts side by side:
- **Reference Image**: Input face image (1 second static)
- **Model A**: First model's generated video
- **Model B**: Second model's generated video

Audio is taken from Model B's position in the concatenation.