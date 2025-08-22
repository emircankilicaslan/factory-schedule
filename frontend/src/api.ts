
import axios from 'axios'
import type { WorkOrder, Operation } from './types'

const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
export const api = axios.create({ baseURL })

export async function fetchWorkOrders(): Promise<WorkOrder[]> {
  const { data } = await api.get<WorkOrder[]>('/workorders')
  // backend uses snake_case; convert to camel_case fields the frontend expects
  const mapped = data.map(wo => ({
    ...wo,
    operations: wo.operations.map(op => ({
      id: op.id,
      workOrderId: (op as any).workOrderId ?? (op as any).work_order_id ?? op.workOrderId,
      index: op.index,
      machineId: (op as any).machineId ?? (op as any).machine_id ?? op.machineId,
      name: op.name,
      start: op.start,
      end: op.end
    }))
  }))
  return mapped
}

export async function updateOperation(id: string, start: string, end: string): Promise<Operation> {
  const { data } = await api.patch(`/operations/${id}`, { start, end })
  // normalize casing
  return {
    id: data.id,
    workOrderId: data.workOrderId ?? data.work_order_id,
    index: data.index,
    machineId: data.machineId ?? data.machine_id,
    name: data.name,
    start: data.start,
    end: data.end
  }
}
