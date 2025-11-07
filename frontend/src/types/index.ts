export interface Campaign {
  id: number;
  name: string;
  campaign_type: string;
  budget: number;
  start_date: string;
  end_date: string;
  product: string;
  created_at: string;
  updated_at: string;
  campaign_urls?: CampaignURL[];
}

export interface CampaignURL {
  id: number;
  url: string;
  channel: string;
  created_at: string;
}

export interface CampaignURLUpdatePayload {
  id: number;
  url: string;
  channel?: string;
}

export interface CampaignCreate {
  name: string;
  campaign_type: string;
  budget: number;
  start_date: string;
  end_date: string;
  product: string;
  urls: CampaignURLCreate[];
}

export interface CampaignURLCreate {
  url: string;
  channel: string;
}

export interface CampaignUpdate {
  budget?: number;
  start_date?: string;
  end_date?: string;
  product?: string;
  campaign_type?: string;
  urls?: CampaignURLUpdatePayload[];
}

export interface InstagramPost {
  id: number;
  post_id: string;
  username: string;
  display_name: string;
  follower_count: number;
  s3_thumbnail_url: string;
  likes_count: number;
  comments_count: number;
  subscription_motivation: string;
  category: string;
  grade: string;
  posted_at: string;
  collected_at: string;
  product?: string;
  collection_date?: string;
  campaign_url?: string;
}

export interface InstagramReel {
  id: number;
  reel_id: string;
  reel_url?: string;
  username: string;
  display_name: string;
  follower_count: number;
  s3_thumbnail_url: string;
  video_view_count: number;
  subscription_motivation: string;
  category: string;
  grade: string;
  grade_avg_views?: number;
  posted_at: string;
  collected_at: string;
  product?: string;
  collection_date?: string;
  campaign_url?: string;
  view_history?: Array<{ date: string; views: number }>;
}

export interface BlogPost {
  id: number;
  url: string;
  username?: string;
  title: string;
  likes_count: number;
  comments_count: number;
  daily_visitors: number;
  posted_at: string;
  collected_at: string;
  rankings?: { [date: string]: string };
}

export interface ReportData {
  campaign: {
    name: string;
    start_date: string;
    end_date: string;
    product: string;
    budget?: number;
  };
  chart_data?: {
    labels: string[];
    data: number[];
  };
}

export interface InstagramPostReport extends ReportData {
  unique_reel_count?: number;
  reels: InstagramReel[];
}

export interface InstagramReelReport extends ReportData {
  unique_reel_count?: number;
  reels: InstagramReel[];
  chart_data_by_reel?: {
    [reelUrl: string]: {
      labels: string[];
      data: number[];
    };
  };
}

export interface BlogReport extends ReportData {
  date_columns: string[];
  blogs: BlogPost[];
}

export interface AdminDashboard {
  statistics: {
    total_campaigns: number;
    active_campaigns: number;
    total_instagram_posts: number;
    total_instagram_reels: number;
    total_blog_posts: number;
  };
  campaigns: Campaign[];
}
