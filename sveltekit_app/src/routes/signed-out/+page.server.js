import { redirect } from "@sveltejs/kit";

export async function load({ request, cookies }) {
  cookies.set("sessionid", "", { maxAge: 0, path: "/" });
  redirect(302, "/#signed-out");
}
