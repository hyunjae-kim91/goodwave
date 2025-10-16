export interface PromptData {
  name: string;
  content: string;
}

class PromptService {
  private baseUrl = '/api/influencer/prompt';
  private defaultName = 'system_prompt';
  private typesUrl = '/api/influencer/prompt-types';

  async savePrompt(content: string, name?: string): Promise<{ message: string; name: string }> {
    const promptType = name?.trim() || this.defaultName;
    const response = await fetch(`${this.baseUrl}/${promptType}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '프롬프트 저장에 실패했습니다.');
    }
    return response.json();
  }

  async loadPrompt(name?: string): Promise<PromptData> {
    const promptType = name?.trim() || this.defaultName;
    const response = await fetch(`${this.baseUrl}/${promptType}`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '프롬프트 로드에 실패했습니다.');
    }
    const data = await response.json();
    return {
      name: promptType,
      content: data.content || ''
    };
  }

  async getPromptTypes(): Promise<string[]> {
    const response = await fetch(this.typesUrl);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || '프롬프트 목록을 불러오지 못했습니다.');
    }
    const data = await response.json();
    const types = Array.isArray(data.prompt_types) ? data.prompt_types : [];
    return types.length ? types : [this.defaultName];
  }
}

export const promptService = new PromptService();
