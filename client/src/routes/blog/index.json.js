import axios from "axios";

let contents = "{}";
axios.get("http://localhost:8000/api/publications")
  .then(function (response) {
	  contents = JSON.stringify(response.data.results);
    // handle success
    console.log(response);
  })
  .catch(function (error) {
    // handle error
    console.log(error);
  })
  .then(function () {
    // always executed
  });


export function get(req, res) {
	res.writeHead(200, {
		'Content-Type': 'application/json'
	});

	res.end(contents);
}