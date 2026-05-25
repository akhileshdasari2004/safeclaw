import { z } from "zod";

export const alertFormSchema = z.object({
  threshold: z.coerce.number().positive("Threshold must be positive"),
  enabled: z.boolean().default(true),
  cooldown_hours: z.coerce.number().min(1).max(168).optional(),
});

export type AlertFormValues = z.infer<typeof alertFormSchema>;
