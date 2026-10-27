// Data hooks (TanStack Query): caching, loading and error states handled for us.
import { useQuery } from '@tanstack/react-query';
import { apiGet } from './client';

const FIVE_MINUTES = 5 * 60 * 1000;

export function useServices() {
  return useQuery({
    queryKey: ['services'],
    queryFn: () => apiGet('/services'),
    staleTime: FIVE_MINUTES,
  });
}

export function useTherapists() {
  return useQuery({
    queryKey: ['therapists'],
    queryFn: () => apiGet('/therapists'),
    staleTime: FIVE_MINUTES,
  });
}

export function useSlots({ serviceId, therapistId, dateFrom, dateTo }) {
  return useQuery({
    queryKey: ['slots', serviceId, therapistId, dateFrom, dateTo],
    queryFn: () =>
      apiGet('/availability', {
        service_id: serviceId,
        therapist_id: therapistId,
        date_from: dateFrom,
        date_to: dateTo,
      }),
    enabled: Boolean(serviceId && dateFrom && dateTo),
  });
}
