export function load({ request, cookies }) {
  return {
    userIsAuthenticated: cookies.get("sessionid") ? true : false,
  };
}
