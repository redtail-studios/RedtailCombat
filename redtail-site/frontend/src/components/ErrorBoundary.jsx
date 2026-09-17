import React from 'react';

// Without this, any uncaught render-time error anywhere in the wrapped tree
// unmounts the whole thing, leaving a blank page until a manual refresh —
// exactly the "page went all black" report this fixes. Catches the error,
// shows a recoverable message instead, and logs it so it's diagnosable.
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught a render error:', error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="min-h-[50vh] flex items-center justify-center p-8 bg-ink">
        <div className="max-w-md text-center">
          <p className="font-pixel text-sm text-pulse mb-3">Something broke on this page.</p>
          <p className="font-mono text-xs text-platinum/50 mb-6">
            {this.state.error?.message || 'An unexpected error occurred.'}
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            className="px-4 py-2.5 font-mono text-xs font-medium bg-pulse text-ink hover:opacity-90 transition-opacity pixel-clip-sm"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }
}
