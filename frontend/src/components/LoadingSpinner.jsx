import React from 'react'

const LoadingSpinner = ({ type = 'inline', size = 'normal' }) => {
  const containerClass =
    type === 'page' ? 'page-loader-container' : type === 'content' ? 'content-loader-container' : 'inline-loader-container'
  const loaderClass = `loader ${size === 'small' ? 'loader-small' : ''}`

  return (
    <div className={containerClass} role="status" aria-live="polite" aria-busy="true">
      <div className={loaderClass}></div>
    </div>
  )
}

export default LoadingSpinner 