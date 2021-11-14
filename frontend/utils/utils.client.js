

function handleAxiosError(axiosError, errorFunc) {
  console.error(axiosError);
  if (axiosError.response) {
    errorFunc({
      statusCode: axiosError.response.status,
      message: axiosError.response.statusText,
    });
  } else {
    errorFunc({
      statusCode: null,
      message: axiosError.code,
    });
  }
  throw axiosError
}

export { handleAxiosError };
