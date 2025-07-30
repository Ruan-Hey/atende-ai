import { useState } from 'react'

const TinyTeamsLogo = ({ className = "logo", width = 120, height = "auto" }) => {
  return (
    <>
      <img 
        src="/tinyteams-logo.png" 
        alt="TinyTeams" 
        className={className}
        style={{
          width: width,
          height: height,
          borderRadius: '8px'
        }}
        onError={(e) => {
          // Se falhar, substituir por div com texto
          e.target.style.display = 'none';
          e.target.nextSibling.style.display = 'flex';
        }}
      />
      <div 
        className={className}
        style={{
          width: width,
          height: height,
          display: 'none',
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
    </>
  )
}

export default TinyTeamsLogo 