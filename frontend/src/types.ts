export type ContentType = 'Filme' | 'Série' | 'Música' | 'Notícia';

export interface Content {
  id: number;
  title: string;
  description: string;
  type: ContentType;
  genres: string[];
  language: string;
  year?: number;
  cover: string;
  rating?: number;
  rating_count?: number;
  popularity: number;
  is_demo: boolean;
  featured?: boolean;
  reason?: string;
}

export interface PreferenceState {
  types: ContentType[];
  genres: string[];
  languages: string[];
  blocked_ids: number[];
  diversity: 'equilibrada' | 'exploradora' | 'foco';
}

export interface Metrics {
  contents: number;
  ratings: number;
  favorites: number;
  active_users: number;
  views: number;
  recommendations: number;
  categories: Record<string, number>;
  top_contents: Array<{
    id: number;
    title: string;
    type: ContentType;
    views: number;
    favorites: number;
    ratings: number;
    average_rating: number | null;
  }>;
  daily_activity: Array<{
    day: string;
    recommendations: number;
    interactions: number;
  }>;
  recent_activity: Array<{
    user_name: string | null;
    content_title: string;
    kind: string;
    created_at: string;
  }>;
  strategy: string;
  data_label: string;
}

export interface AuthUser {
  user_id: string;
  name: string;
  email?: string | null;
  role: 'admin' | 'user';
  demo?: boolean;
}
