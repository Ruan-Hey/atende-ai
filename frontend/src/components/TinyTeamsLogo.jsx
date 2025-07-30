import { useState } from 'react'

const TinyTeamsLogo = ({ className = "logo", width = 120, height = "auto" }) => {
  // Sempre usar fallback de texto
  return (
    <div 
      className={className}
      style={{
        width: width,
        height: height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#fff',
        borderRadius: '8px',
        padding: '8px',
        fontWeight: 'bold',
        fontSize: '14px',
        color: '#000',
        textAlign: 'center'
      }}
    >
      TinyTeams
    </div>
  )
}

export default TinyTeamsLogo 