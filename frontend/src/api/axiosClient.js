import axios from "axios";
import { env } from "../config/env";

console.log("API Base URL:", env.apiBaseUrl);

export const axiosClient = axios.create({
  baseURL: env.apiBaseUrl
});