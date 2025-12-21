/**
 * Vitest test setup file
 * Provides mocks for jsdom limitations (canvas, etc.)
 */

// Mock canvas getContext for jsdom
const mockContext2D = {
    fillRect: () => {},
    clearRect: () => {},
    getImageData: () => ({ data: new Array(4) }),
    putImageData: () => {},
    createImageData: () => [],
    setTransform: () => {},
    drawImage: () => {},
    save: () => {},
    restore: () => {},
    beginPath: () => {},
    moveTo: () => {},
    lineTo: () => {},
    closePath: () => {},
    stroke: () => {},
    fill: () => {},
    arc: () => {},
    rect: () => {},
    translate: () => {},
    rotate: () => {},
    scale: () => {},
    measureText: () => ({ width: 0 }),
    fillText: () => {},
    strokeText: () => {},
    clip: () => {},
    quadraticCurveTo: () => {},
    bezierCurveTo: () => {},
    isPointInPath: () => false,
    isPointInStroke: () => false,
    canvas: { width: 300, height: 150 },
    // Properties
    fillStyle: '#000000',
    strokeStyle: '#000000',
    lineWidth: 1,
    lineCap: 'butt',
    lineJoin: 'miter',
    font: '10px sans-serif',
    textAlign: 'start',
    textBaseline: 'alphabetic',
    globalAlpha: 1,
    globalCompositeOperation: 'source-over',
};

// Store original getContext
const originalGetContext = HTMLCanvasElement.prototype.getContext;

// Override getContext
HTMLCanvasElement.prototype.getContext = function (type) {
    if (type === '2d') {
        return mockContext2D;
    }
    // Try original for other contexts (webgl, etc.)
    try {
        return originalGetContext.call(this, type);
    } catch (e) {
        return null;
    }
};

// Mock toDataURL
HTMLCanvasElement.prototype.toDataURL = function (type = 'image/png') {
    return `data:${type};base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==`;
};

// Mock toBlob
HTMLCanvasElement.prototype.toBlob = function (callback, type = 'image/png') {
    const base64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    const binary = atob(base64);
    const array = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        array[i] = binary.charCodeAt(i);
    }
    const blob = new Blob([array], { type });
    callback(blob);
};

console.log('✓ Canvas mocks installed for jsdom');
