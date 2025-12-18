// User types
export interface User {
  id: string;
  username: string;
  email: string;
  is_staff: boolean;
}

// Auth types
export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
}

// Chat types
export interface FileAttachment {
  name: string;
  size: number;
  type: string;
  url?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  agent?: string;
  created_at: string;
  file?: FileAttachment;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface Source {
  key?: string;
  content?: string;
  metadata?: Record<string, unknown>;
  similarity?: number;
}

// Document types
export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  file_size_display: string;
  document_key: string;
  file_url: string;
  is_vectorized: boolean;
  is_persistent: boolean;
  chunk_count: number;
  created_at: string;
}

// SSE Event types
export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

// API Response types
export interface ApiResponse<T = unknown> {
  success: boolean;
  message?: string;
  errors?: Record<string, string[]>;
  data?: T;
}

// Chat request
export interface ChatRequest {
  message: string;
  conversation_id?: string;
  document_key?: string;
  persist_embeddings?: boolean;
}

// Admin types
export interface AdminStats {
  total_users: number;
  total_conversations: number;
  total_messages: number;
  total_documents: number;
}

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
  conversation_count: number;
  document_count: number;
}
