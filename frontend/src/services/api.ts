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
    api.get(`/api/unified-reports/instagram/unified/${campaignName}`).then(res => res.data),
  
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
  
  getCampaignCollectionStatus: (): Promise<any> =>
    api.get('/api/admin/campaign-collection-status').then(res => res.data),
  
  getCampaignCollectionStatusById: (campaignId: number): Promise<any> =>
    api.get(`/api/admin/campaign-collection-status/${campaignId}`).then(res => res.data),
  
  processReelCollectionJobs: (): Promise<{ message: string; processed_count: number }> =>
    api.post('/api/admin/process-reel-collection-jobs').then(res => res.data),
  
  retryFailedReelJobs: (campaignId?: number): Promise<{ message: string; retried_count: number }> =>
    api.post('/api/admin/retry-failed-reel-jobs', {}, {
      params: campaignId ? { campaign_id: campaignId } : {}
    }).then(res => res.data),
  
  cancelProcessingReelJobs: (campaignId?: number): Promise<{ message: string; cancelled_count: number }> =>
    api.post('/api/admin/cancel-processing-reel-jobs', {}, {
      params: campaignId ? { campaign_id: campaignId } : {}
    }).then(res => res.data),
  
  stopCollectionWorker: (): Promise<{ message: string; status: string }> =>
    api.post('/api/admin/stop-collection-worker').then(res => res.data),
  
  getCollectionWorkerStatus: (): Promise<{ worker_status: any; message: string }> =>
    api.get('/api/admin/collection-worker-status').then(res => res.data),
  
  cancelProcessingJobs: (): Promise<{ message: string; cancelled_count: number; worker_stopped: boolean }> =>
    api.post('/api/admin/cancel-processing-jobs').then(res => res.data),
  
  deletePendingJobs: (campaignId?: number): Promise<{ message: string; deleted_count: number }> =>
    api.delete('/api/admin/delete-pending-jobs', {
      params: campaignId ? { campaign_id: campaignId } : {}
    }).then(res => res.data),
  
  deleteFailedJobs: (campaignId?: number): Promise<{ message: string; deleted_count: number }> =>
    api.delete('/api/admin/delete-failed-jobs', {
      params: campaignId ? { campaign_id: campaignId } : {}
    }).then(res => res.data),
  
  deleteCompletedJobs: (campaignId?: number): Promise<{ message: string; deleted_count: number }> =>
    api.delete('/api/admin/delete-completed-jobs', {
      params: campaignId ? { campaign_id: campaignId } : {}
    }).then(res => res.data),
  
  retryFailedCollectionJobs: (): Promise<{ message: string; retried_count: number }> =>
    api.post('/api/admin/retry-failed-collection-jobs').then(res => res.data),
  
  retrySelectedInfluencerJobs: (jobIds: string[]): Promise<{ success: boolean; message: string; retried_count: number }> =>
    api.post('/api/influencer/collection-jobs/retry', jobIds).then(res => res.data),
  
  // Influencer collection queue management
  getInfluencerWorkerStatus: (): Promise<{ success: boolean; status: any }> =>
    api.get('/api/influencer/worker/status').then(res => res.data),
  
  stopInfluencerProcessingJobs: (): Promise<{ success: boolean; message: string; stopped_count: number }> =>
    api.post('/api/influencer/collection-jobs/stop-processing').then(res => res.data),
  
  stopAllInfluencerJobs: (): Promise<{ success: boolean; message: string; stopped_count: number; worker_status: any }> =>
    api.post('/api/influencer/collection-jobs/stop-all').then(res => res.data),
  
  getInfluencerCollectionJobs: (status?: string, limit?: number, offset?: number): Promise<{ success: boolean; total: number; jobs: any[]; pagination: any }> =>
    api.get('/api/influencer/collection-jobs', { params: { status, limit, offset } }).then(res => res.data),
  
  getInfluencerCollectionSummary: (): Promise<{ success: boolean; summary: any }> =>
    api.get('/api/influencer/collection-jobs/summary').then(res => res.data),
};

export default api;
