/**
 * Sentry Error Monitoring - Frontend Configuration
 * Tracks errors, performance, and user interactions
 */
/// <reference types="vite/client" />
import * as Sentry from '@sentry/react';

export function initSentry() {
  const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
  const environment = import.meta.env.VITE_ENVIRONMENT || 'development';

  if (!sentryDsn) {
    console.warn('[SENTRY] VITE_SENTRY_DSN not set - error monitoring disabled');
    console.info('[SENTRY] To enable Sentry:');
    console.info('[SENTRY] 1. Sign up at https://sentry.io');
    console.info('[SENTRY] 2. Create a new React project');
    console.info('[SENTRY] 3. Add VITE_SENTRY_DSN=<your-dsn> to frontend/.env');
    return false;
  }

  try {
    Sentry.init({
      dsn: sentryDsn,
      environment,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: false,
          blockAllMedia: false,
        }),
      ],

      // Performance Monitoring
      tracesSampleRate: environment === 'development' ? 1.0 : 0.1, // 100% in dev, 10% in prod

      // Session Replay
      replaysSessionSampleRate: 0.1, // 10% of sessions
      replaysOnErrorSampleRate: 1.0, // 100% of sessions with errors

      // Filter sensitive data
      beforeSend(event, _hint) {
        // Remove sensitive headers
        if (event.request?.headers) {
          delete event.request.headers['Authorization'];
          delete event.request.headers['Cookie'];
        }

        // Add custom tags for better filtering
        if (event.exception) {
          const errorMessage = event.exception.values?.[0]?.value || '';

          // Tag citation-related errors
          if (errorMessage.toLowerCase().includes('citation')) {
            event.tags = { ...event.tags, error_category: 'citation' };
          }

          // Tag document viewer errors
          if (errorMessage.toLowerCase().includes('document') || errorMessage.toLowerCase().includes('viewer')) {
            event.tags = { ...event.tags, error_category: 'document_viewer' };
          }

          // Tag API errors
          if (errorMessage.toLowerCase().includes('fetch') || errorMessage.toLowerCase().includes('api')) {
            event.tags = { ...event.tags, error_category: 'api' };
          }
        }

        return event;
      },

      // Release tracking
      release: import.meta.env.VITE_APP_VERSION || '1.0.0',
    });

    console.info('[SENTRY] Initialized successfully (environment: ' + environment + ')');
    return true;
  } catch (error) {
    console.error('[SENTRY] Failed to initialize:', error);
    return false;
  }
}

/**
 * Capture citation display issues
 */
export function captureCitationIssue(
  message: string,
  context?: Record<string, any>
) {
  Sentry.withScope((scope) => {
    scope.setTag('issue_type', 'citation');
    if (context) {
      scope.setContext('citation', context);
    }
    Sentry.captureMessage(message, 'warning');
  });
}

/**
 * Capture document viewer issues
 */
export function captureDocumentViewerIssue(
  fileName: string,
  error: Error,
  context?: Record<string, any>
) {
  Sentry.withScope((scope) => {
    scope.setTag('issue_type', 'document_viewer');
    scope.setTag('file_type', fileName.split('.').pop() || 'unknown');
    if (context) {
      scope.setContext('document_viewer', {
        fileName,
        ...context,
      });
    }
    Sentry.captureException(error);
  });
}
