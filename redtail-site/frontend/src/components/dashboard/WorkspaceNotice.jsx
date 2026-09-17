export default function WorkspaceNotice({ children, error = false }) {
  return <div className={`dw-notice ${error ? 'dw-error' : ''}`} role={error ? 'alert' : 'status'}>{children}</div>;
}
