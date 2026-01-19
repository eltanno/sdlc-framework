import express, { Express, Request, Response } from 'express';
import dotenv from 'dotenv';
import { userRouter } from './routes/users';
import { healthRouter } from './routes/health';

dotenv.config();

const app: Express = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.use('/api/users', userRouter);
app.use('/api/health', healthRouter);

// Root endpoint
app.get('/', (req: Request, res: Response) => {
  res.json({ message: 'Welcome to the TypeScript Sample API' });
});

// TODO: Add authentication middleware
// FIXME: Rate limiting is not implemented

app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
});

export default app;
