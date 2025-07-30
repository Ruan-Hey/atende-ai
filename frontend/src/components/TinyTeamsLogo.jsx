import { useState } from 'react'

const TinyTeamsLogo = ({ className = "logo", width = 120, height = "auto" }) => {
  const [imageError, setImageError] = useState(false)

  const handleImageError = () => {
    setImageError(true)
  }

  if (imageError) {
    // Fallback: texto estilizado
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

  return (
    <img 
              src="https://via.placeholder.com/120x40/000000/FFFFFF?text=TinyTeams" 
      alt="TinyTeams" 
      className={className}
      style={{ width, height }}
      onError={handleImageError}
      onLoad={() => console.log('Logo TinyTeams carregada com sucesso!')}
    />
  )
}

export default TinyTeamsLogo 