import { redirect } from "@sveltejs/kit";

export async function load({ request, cookies }) {

  const API_URL = "http://localhost:8091/api/v0?format=json";

  const userRequest = await fetch(API_URL, {
    headers: {
      cookie: `sessionid=${cookies.get("sessionid")}`,
    },
  });
  const userData = userRequest.ok ? await userRequest.json() : {};

  const publicRoutes = [
    "/",
    "/sign-in",
    "/privacy",
    "/accessibility",
    "support",
    "sitemap",
  ];
  // TO DO: Add a redirect here if user is not authenticated, unless one of the publicRoutes

  return {
    userIsAuthenticated: userData.email ? true : false,
    user: userData,
  };
  
}
