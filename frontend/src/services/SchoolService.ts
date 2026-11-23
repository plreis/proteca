import { Classroom } from '@/types';
import { authenticatedApiRequest } from './api';

interface SchoolResponse {
  id: string;
  name: string;
  city: string;
}

interface ClassroomResponse {
  id: string;
  school_id: string;
  name: string;
  grade: string;
}

export const schoolService = {
  getSchool(): Promise<SchoolResponse> {
    return authenticatedApiRequest('/school');
  },

  async getClassrooms(): Promise<Classroom[]> {
    const response =
      await authenticatedApiRequest<ClassroomResponse[]>('/classrooms');

    return response.map((classroom) => ({
      id: classroom.id,
      schoolId: classroom.school_id,
      name: classroom.name,
      grade: classroom.grade, 
    }));
  },
};