module.exports = {
  workers: 1, // to prevent issues with magic links
  use: {
    baseURL: "http://localhost:8091",
    retries: 2,
  },
};
