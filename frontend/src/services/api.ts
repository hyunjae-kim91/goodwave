import axios from 'axios';
import {
  Campaign,
  CampaignCreate,
  CampaignUpdate,
  InstagramPost,
  InstagramReel,
  BlogPost,
  InstagramPostReport,
  InstagramReelReport,
  BlogReport,
  AdminDashboard
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Campaigns API
export const campaignsApi = {
  create: (data: CampaignCreate): Promise<Campaign> =>
    api.post('/api/campaigns/', data).then(res => res.data),
  
  getAll: (): Promise<Campaign[]> =>
    api.get('/api/campaigns/').then(res => res.data),
  
  getById: (id: number): Promise<Campaign> =>
    api.get(`/api/campaigns/${id}`).then(res => res.data),

  update: (id: number, data: CampaignUpdate): Promise<Campaign> =>
    api.put(`/api/campaigns/${id}`, data).then(res => res.data),
  
  delete: (id: number): Promise<{ message: string }> =>
    api.delete(`/api/campaigns/${id}`).then(res => res.data),
};


// Reports API
export const reportsApi = {
  getInstagramPostReport: (campaignName: string): Promise<InstagramPostReport> =>
    api.get(`/api/reports/instagram/posts/${campaignName}`).then(res => res.data),
  
  getInstagramReelReport: (campaignName: string): Promise<InstagramReelReport> =>
    api.get(`/api/reports/instagram/reels/${campaignName}`).then(res => res.data),
  
  getBlogReport: (campaignName: string): Promise<BlogReport> =>
    api.get(`/api/reports/blogs/${campaignName}`).then(res => res.data),
  
  getAvailableCampaigns: (): Promise<Campaign[]> =>
    api.get('/api/reports/campaigns').then(res => res.data),
};

// Admin API
export const adminApi = {
  getDashboard: (): Promise<AdminDashboard> =>
    api.get('/api/admin/dashboard').then(res => res.data),
  
  getCollectionSchedules: (): Promise<any[]> =>
    api.get('/api/admin/collection-schedules').then(res => res.data),
  
  toggleCollectionSchedule: (scheduleId: number): Promise<{ message: string; is_active: boolean }> =>
    api.put(`/api/admin/collection-schedules/${scheduleId}/toggle`).then(res => res.data),
};

export default api;
