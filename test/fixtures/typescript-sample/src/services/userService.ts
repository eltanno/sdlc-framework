import axios from 'axios';

interface User {
  id: string;
  name: string;
  email: string;
  createdAt: Date;
}

interface CreateUserDto {
  name: string;
  email: string;
}

// TODO: Replace with actual database
const users: User[] = [
  { id: '1', name: 'John Doe', email: 'john@example.com', createdAt: new Date() },
  { id: '2', name: 'Jane Smith', email: 'jane@example.com', createdAt: new Date() },
];

export class UserService {
  private apiBaseUrl: string;

  constructor() {
    this.apiBaseUrl = process.env.API_BASE_URL || 'https://api.example.com';
  }

  async getAllUsers(): Promise<User[]> {
    // HACK: Using in-memory store instead of database
    return users;
  }

  async getUserById(id: string): Promise<User | undefined> {
    return users.find(user => user.id === id);
  }

  async createUser(dto: CreateUserDto): Promise<User> {
    const newUser: User = {
      id: String(users.length + 1),
      name: dto.name,
      email: dto.email,
      createdAt: new Date(),
    };
    users.push(newUser);
    return newUser;
  }

  // External API integration example
  async fetchExternalUserData(userId: string): Promise<any> {
    const response = await axios.get(`${this.apiBaseUrl}/users/${userId}`);
    return response.data;
  }
}
