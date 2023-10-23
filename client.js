const response = await fetch('https://web-api.palatialxr.com:3001:generate-url', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url: 'testing' })
});

if (response.ok) {
  const data = await response.json();
  console.log(data);
}
