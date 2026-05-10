import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const reviews = defineCollection({
  loader: glob({ pattern: '**/[^_]*.md', base: './src/content/reviews' }),
  schema: z.object({
    title: z.string(),
    date: z.string(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { reviews };
