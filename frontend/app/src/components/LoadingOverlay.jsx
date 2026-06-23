export default function LoadingOverlay() {
  return (
    <div className="loading-overlay" aria-live="polite" aria-busy="true">
      <div className="spinner spinner--large" />
    </div>
  )
}
