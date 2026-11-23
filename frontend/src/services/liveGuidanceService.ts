import { LiveGuidance } from '@/types';
import { authenticatedApiRequest } from './api';

interface LiveGuidanceResponse {
  session_id: string;
  model: string;
  generated_at: string;
  attention_level: string;
  observed_pattern: string;
  teacher_suggestions: string[];
  intervention: LiveGuidance['intervention'];
  limitations: string;
  is_mock: boolean;
}

export async function requestLiveGuidance(
  sessionId: string
): Promise<LiveGuidance> {
  const data = await authenticatedApiRequest<LiveGuidanceResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/live`,
    { method: 'POST' }
  );

  return {
    sessionId: data.session_id,
    model: data.model,
    generatedAt: data.generated_at,
    attentionLevel: data.attention_level,
    observedPattern: data.observed_pattern,
    teacherSuggestions: data.teacher_suggestions,
    intervention: data.intervention,
    limitations: data.limitations,
    isMock: data.is_mock,
  };
}
