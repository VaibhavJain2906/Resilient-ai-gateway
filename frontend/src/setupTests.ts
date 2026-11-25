import '@testing-library/jest-dom/vitest';

// Polyfill window.scrollTo and Element.scrollIntoView in jsdom
Element.prototype.scrollIntoView = () => {};
window.scrollTo = () => {};
