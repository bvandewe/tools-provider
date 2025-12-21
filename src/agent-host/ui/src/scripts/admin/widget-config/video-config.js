/**
 * Video Widget Configuration
 *
 * Configuration UI for the 'video' widget type.
 *
 * Python Schema Reference (VideoConfig):
 * - src: str (required) - video URL
 * - poster: str | None - thumbnail image URL
 * - title: str | None - video title
 * - duration: float | None - video duration in seconds
 * - autoplay: bool | None
 * - muted: bool | None
 * - loop: bool | None
 * - controls: VideoControls | None
 * - playback_speeds: list[float] | None (alias: playbackSpeeds)
 * - captions: list[VideoCaption] | None
 * - qualities: list[VideoQuality] | None
 * - checkpoints: list[VideoCheckpoint] | None
 * - chapters: list[VideoChapter] | None
 * - required_watch_percentage: float | None (alias: requiredWatchPercentage)
 * - prevent_skip_ahead: bool | None (alias: preventSkipAhead)
 * - track_progress: bool | None (alias: trackProgress)
 *
 * VideoControls:
 * - play, pause, seek, volume, fullscreen, playback_speed, captions, quality (all bool | None)
 *
 * VideoCaption:
 * - language: str, label: str, src: str
 *
 * VideoQuality:
 * - label: str, src: str
 *
 * VideoChapter:
 * - title: str, start_time: float (alias: startTime)
 *
 * VideoCheckpoint:
 * - checkpoint_id: str, timestamp: float, pause_on_reach?, required?, widget?, action?, note?
 *
 * @module admin/widget-config/video-config
 */

import { WidgetConfigBase } from './config-base.js';

export class VideoConfig extends WidgetConfigBase {
    /**
     * Render the video widget configuration UI
     * @param {Object} config - Widget configuration
     * @param {Object} content - Full content object
     */
    render(config = {}, content = {}) {
        const controls = config.controls || {};

        // Convert chapters to text format: title|startTime
        const chapters = config.chapters || [];
        const chaptersText = chapters.map(ch => `${ch.title}|${ch.start_time ?? ch.startTime ?? 0}`).join('\n');

        // Convert captions to text format: language|label|src
        const captions = config.captions || [];
        const captionsText = captions.map(cap => `${cap.language}|${cap.label}|${cap.src}`).join('\n');

        // Convert playback speeds to comma-separated string
        const speeds = config.playback_speeds ?? config.playbackSpeeds ?? [];
        const speedsText = speeds.join(', ');

        this.container.innerHTML = `
            <div class="widget-config widget-config-video">
                <div class="row g-2">
                    <div class="col-md-8">
                        ${this.createFormGroup('Video URL', this.createTextInput('config-src', config.src ?? '', 'https://example.com/video.mp4'), 'URL of the video file or stream.', true)}
                    </div>
                    <div class="col-md-4">
                        ${this.createFormGroup('Duration (seconds)', this.createNumberInput('config-duration', config.duration ?? '', 0, 36000, 1), 'Total video duration (for progress display).')}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-6">
                        ${this.createFormGroup('Title', this.createTextInput('config-title', config.title ?? '', 'Video Title'), 'Display title for the video.')}
                    </div>
                    <div class="col-md-6">
                        ${this.createFormGroup(
                            'Poster Image URL',
                            this.createTextInput('config-poster', config.poster ?? '', 'https://example.com/poster.jpg'),
                            'Thumbnail image shown before playback.'
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-2">
                        ${this.createSwitch('config-autoplay', `${this.uid}-autoplay`, 'Autoplay', 'Start playing automatically.', config.autoplay ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-muted', `${this.uid}-muted`, 'Muted', 'Start with audio muted.', config.muted ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-loop', `${this.uid}-loop`, 'Loop', 'Loop video continuously.', config.loop ?? false)}
                    </div>
                    <div class="col-md-2">
                        ${this.createSwitch('config-track-progress', `${this.uid}-track-progress`, 'Track Progress', 'Track viewing progress.', config.track_progress ?? config.trackProgress ?? false)}
                    </div>
                    <div class="col-md-4">
                        ${this.createSwitch(
                            'config-prevent-skip',
                            `${this.uid}-prevent-skip`,
                            'Prevent Skip Ahead',
                            'Disable seeking ahead in video.',
                            config.prevent_skip_ahead ?? config.preventSkipAhead ?? false
                        )}
                    </div>
                </div>

                <div class="row g-2 mt-2">
                    <div class="col-md-4">
                        ${this.createFormGroup(
                            'Required Watch %',
                            this.createNumberInput('config-watch-pct', config.required_watch_percentage ?? config.requiredWatchPercentage ?? '', 0, 100, 5),
                            'Percentage of video that must be watched (0-100).'
                        )}
                    </div>
                    <div class="col-md-8">
                        ${this.createFormGroup('Playback Speeds', this.createTextInput('config-speeds', speedsText, '0.5, 0.75, 1, 1.25, 1.5, 2'), 'Comma-separated list of playback speeds.')}
                    </div>
                </div>

                ${this.createCollapsibleSection(
                    `${this.uid}-controls`,
                    'Player Controls',
                    `
                    <div class="row g-2">
                        <div class="col-md-3">
                            ${this.createSwitch('config-ctrl-play', `${this.uid}-ctrl-play`, 'Play/Pause', '', controls.play ?? true)}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-ctrl-seek', `${this.uid}-ctrl-seek`, 'Seek Bar', '', controls.seek ?? true)}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-ctrl-volume', `${this.uid}-ctrl-volume`, 'Volume', '', controls.volume ?? true)}
                        </div>
                        <div class="col-md-3">
                            ${this.createSwitch('config-ctrl-fullscreen', `${this.uid}-ctrl-fullscreen`, 'Fullscreen', '', controls.fullscreen ?? true)}
                        </div>
                    </div>
                    <div class="row g-2 mt-2">
                        <div class="col-md-4">
                            ${this.createSwitch('config-ctrl-speed', `${this.uid}-ctrl-speed`, 'Speed Control', '', controls.playback_speed ?? controls.playbackSpeed ?? true)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-ctrl-captions', `${this.uid}-ctrl-captions`, 'Captions', '', controls.captions ?? true)}
                        </div>
                        <div class="col-md-4">
                            ${this.createSwitch('config-ctrl-quality', `${this.uid}-ctrl-quality`, 'Quality Selector', '', controls.quality ?? true)}
                        </div>
                    </div>
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-chapters`,
                    'Chapters',
                    `
                    ${this.createFormGroup(
                        'Chapter Markers',
                        this.createTextarea('config-chapters', chaptersText, 'Introduction|0\nMain Content|120\nConclusion|480', 4),
                        'One chapter per line. Format: title|startTime (seconds)'
                    )}
                `
                )}

                ${this.createCollapsibleSection(
                    `${this.uid}-captions`,
                    'Captions',
                    `
                    ${this.createFormGroup(
                        'Caption Tracks',
                        this.createTextarea('config-captions', captionsText, 'en|English|https://example.com/en.vtt\nes|Spanish|https://example.com/es.vtt', 3),
                        'One caption per line. Format: language|label|url'
                    )}
                `
                )}
            </div>
        `;

        this.initTooltips();
    }

    /**
     * Parse chapters from textarea
     * @returns {Array|null} Parsed chapters array or null
     */
    parseChapters() {
        const text = this.getInputValue('config-chapters', '');
        if (!text.trim()) return null;

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                return {
                    title: parts[0],
                    start_time: parseFloat(parts[1]) || 0,
                };
            });
    }

    /**
     * Parse captions from textarea
     * @returns {Array|null} Parsed captions array or null
     */
    parseCaptions() {
        const text = this.getInputValue('config-captions', '');
        if (!text.trim()) return null;

        return text
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)
            .map(line => {
                const parts = line.split('|').map(p => p.trim());
                return {
                    language: parts[0],
                    label: parts[1] || parts[0],
                    src: parts[2] || '',
                };
            });
    }

    /**
     * Parse playback speeds from text input
     * @returns {Array|null} Parsed speeds array or null
     */
    parseSpeeds() {
        const text = this.getInputValue('config-speeds', '');
        if (!text.trim()) return null;

        return text
            .split(',')
            .map(s => parseFloat(s.trim()))
            .filter(n => !isNaN(n) && n > 0);
    }

    /**
     * Get configuration values matching Python schema
     * @returns {Object} Widget configuration
     */
    getValue() {
        const config = {};

        config.src = this.getInputValue('config-src', '');

        const title = this.getInputValue('config-title');
        if (title) config.title = title;

        const poster = this.getInputValue('config-poster');
        if (poster) config.poster = poster;

        const duration = this.getInputValue('config-duration');
        if (duration) {
            const parsed = parseFloat(duration);
            if (!isNaN(parsed) && parsed > 0) config.duration = parsed;
        }

        const autoplay = this.getChecked('config-autoplay');
        if (autoplay) config.autoplay = true;

        const muted = this.getChecked('config-muted');
        if (muted) config.muted = true;

        const loop = this.getChecked('config-loop');
        if (loop) config.loop = true;

        const trackProgress = this.getChecked('config-track-progress');
        if (trackProgress) config.track_progress = true;

        const preventSkip = this.getChecked('config-prevent-skip');
        if (preventSkip) config.prevent_skip_ahead = true;

        const watchPct = this.getInputValue('config-watch-pct');
        if (watchPct) {
            const parsed = parseFloat(watchPct);
            if (!isNaN(parsed) && parsed > 0) config.required_watch_percentage = parsed;
        }

        // Build controls object
        const controls = {};
        controls.play = this.getChecked('config-ctrl-play');
        controls.seek = this.getChecked('config-ctrl-seek');
        controls.volume = this.getChecked('config-ctrl-volume');
        controls.fullscreen = this.getChecked('config-ctrl-fullscreen');
        controls.playback_speed = this.getChecked('config-ctrl-speed');
        controls.captions = this.getChecked('config-ctrl-captions');
        controls.quality = this.getChecked('config-ctrl-quality');

        // Only include controls if any are disabled (otherwise use defaults)
        const allEnabled = Object.values(controls).every(v => v);
        if (!allEnabled) {
            config.controls = controls;
        }

        const speeds = this.parseSpeeds();
        if (speeds && speeds.length > 0) config.playback_speeds = speeds;

        const chapters = this.parseChapters();
        if (chapters && chapters.length > 0) config.chapters = chapters;

        const captions = this.parseCaptions();
        if (captions && captions.length > 0) config.captions = captions;

        return config;
    }

    /**
     * Validate configuration
     * @returns {{valid: boolean, errors: string[]}} Validation result
     */
    validate() {
        const errors = [];

        const src = this.getInputValue('config-src', '');
        if (!src) {
            errors.push('Video URL is required');
        }

        // Validate captions format
        const captions = this.parseCaptions();
        if (captions) {
            for (const cap of captions) {
                if (!cap.language || !cap.src) {
                    errors.push('Captions must have language and URL');
                    break;
                }
            }
        }

        // Validate watch percentage
        const watchPct = this.getInputValue('config-watch-pct');
        if (watchPct) {
            const parsed = parseFloat(watchPct);
            if (isNaN(parsed) || parsed < 0 || parsed > 100) {
                errors.push('Required watch percentage must be between 0 and 100');
            }
        }

        return { valid: errors.length === 0, errors };
    }
}
