export interface Task8SmokeServer {
  origin: string
  close(): Promise<void>
}

export function createTask8SmokeServer(options?: { port?: number }): Promise<Task8SmokeServer>
