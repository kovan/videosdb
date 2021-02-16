function handleAxiosError(axiosError, errorFunc) {
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

export default handleAxiosError
