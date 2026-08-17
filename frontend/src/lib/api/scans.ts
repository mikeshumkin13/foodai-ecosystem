import { apiRequest } from "./client";
import type {
  FoodScanConfirmResponse,
  FoodScanDetectedItem,
  FoodScanResult,
  FoodScanUploadResponse,
} from "./types";

export type ScanItemUpdatePayload = {
  food_id?: string;
  mass_g?: string;
};

export type ScanItemAddPayload = {
  food_id: string;
  mass_g: string;
  label?: string;
};

export const scansApi = {
  upload(photo: File) {
    const formData = new FormData();
    formData.set("photo", photo);

    return apiRequest<FoodScanUploadResponse>("/api/v1/food-scans/", {
      method: "POST",
      body: formData,
    });
  },
  result(scanId: string) {
    return apiRequest<FoodScanResult>(`/api/v1/food-scans/${scanId}/results/`);
  },
  retry(scanId: string) {
    return apiRequest<FoodScanUploadResponse>(`/api/v1/food-scans/${scanId}/retry/`, {
      method: "POST",
    });
  },
  updateItem(scanId: string, itemId: string, payload: ScanItemUpdatePayload) {
    return apiRequest<FoodScanDetectedItem>(`/api/v1/food-scans/${scanId}/items/${itemId}/`, {
      method: "PATCH",
      body: payload,
    });
  },
  addItem(scanId: string, payload: ScanItemAddPayload) {
    return apiRequest<FoodScanDetectedItem>(`/api/v1/food-scans/${scanId}/items/`, {
      method: "POST",
      body: payload,
    });
  },
  removeItem(scanId: string, itemId: string) {
    return apiRequest<void>(`/api/v1/food-scans/${scanId}/items/${itemId}/`, {
      method: "DELETE",
    });
  },
  confirm(scanId: string, payload: { meal_type: string; logged_at?: string; name?: string }) {
    return apiRequest<FoodScanConfirmResponse>(`/api/v1/food-scans/${scanId}/confirm/`, {
      method: "POST",
      body: payload,
    });
  },
};
