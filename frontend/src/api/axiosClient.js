import axios from "axios";

import { env } from "../config/env";

export const axiosClient = axios.create({
  baseURL: env.apiBaseUrl
});
