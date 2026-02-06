/**
 * Services Index
 *
 * Central export for all API service modules.
 */

export * from './studentService';
export * from './businessService';

// Default exports
export { default as studentService } from './studentService';
export { default as businessService } from './businessService';
