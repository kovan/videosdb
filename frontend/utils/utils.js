function handleAxiosError(axiosError, errorFunc) {
  console.error(axiosError)
  if (axiosError.response) {
    errorFunc({
      statusCode: axiosError.response.status,
      message: axiosError.response.statusText,
    })
  } else {
    errorFunc({
      statusCode: null,
      message: axiosError.code,
    })
  }
}
function getConfigForRequest(req) {
  const host = req?
    req.headers.host.split(':')[0]
    : (typeof(window) != "undefined") ? 
      window.location.host.split(':')[0]
      : null;
    

  var config = null

  switch (host) {
    case 'nithyananda.yoga':
      config = {
        domain: 'nithyananda.yoga',
        title: "KAILASA's Nithyananda",
        subtitle: '',
        gcs_url: 'https://cse.google.com/cse.js?cx=043c6e15fcd358d5a',
      }
      break
    default:
    case 'sadhguru.digital':
      config = {
        domain: 'sadhguru.digital',
        title: 'Sadhguru wisdom',
        subtitle:
          'Mysticism, yoga, spirituality, day-to-day life tips, ancient wisdom, interviews, tales, and much more.',
        gcs_url: 'https://cse.google.com/cse.js?cx=7c33eb2b1fc2db635',
      }
      break
  }

  return config
}

export { handleAxiosError, getConfigForRequest }
