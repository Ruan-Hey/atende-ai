import React from 'react'

const LoadingSpinner = ({ type = 'content', size = 'normal' }) => {
  const containerClass = type === 'page' ? 'page-loader-container' : 'content-loader-container'
  const loaderClass = `loader ${size === 'small' ? 'loader-small' : ''}`
  
  return (
    <div className={containerClass}>
      <div className={loaderClass}></div>
    </div>
  )
}

export default LoadingSpinner 