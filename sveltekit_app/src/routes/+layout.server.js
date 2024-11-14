//import { redirect } from "@sveltejs/kit";
import { config } from 'dotenv';
config();

export async function load({ request, cookies }) {

  const API_URL = `${process.env.DJANGO_API_HOST}/api/v0?format=json`;

  let userData = {};

  try {
    const userRequest = await fetch(API_URL, {
      headers: {
        cookie: `sessionid=${cookies.get("sessionid")}`,
      },
    });
    userData = userRequest.ok ? await userRequest.json() : {};
  } catch (err) {
    console.log("Error connecting to Django", err);
  }
  

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
