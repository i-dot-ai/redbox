//import { security } from '$lib/server/envs';

import { config } from 'dotenv';
config();

export function load() {
	return {
		security: process.env.MAX_SECURITY_CLASSIFICATION?.replace('_', ' '),
		allowSignUps: process.env.ALLOW_SIGN_UPS === 'True'
	};
}
