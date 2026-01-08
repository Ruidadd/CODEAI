import Stripe from 'stripe'

// Initialize Stripe only if API key is available
const getStripe = () => {
  const key = process.env.STRIPE_SECRET_KEY
  if (!key) {
    throw new Error('STRIPE_SECRET_KEY is not configured')
  }
  return new Stripe(key, {
    apiVersion: '2025-12-15.clover',
    typescript: true,
  })
}

export { getStripe as stripe }

export const PLANS = {
  free: {
    name: 'Free',
    description: 'Get started with basic features',
    price: 0,
    priceId: '',
    features: [
      '5 generations per day',
      '2 projects',
      'Basic AI models',
      'Community support',
    ],
    limits: {
      generationsPerDay: 5,
      maxProjects: 2,
    },
  },
  pro: {
    name: 'Pro',
    description: 'For professionals and growing teams',
    price: 19,
    priceId: process.env.STRIPE_PRO_PRICE_ID || '',
    features: [
      '100 generations per day',
      'Unlimited projects',
      'All AI models (Gemini, Claude, GPT)',
      'Priority support',
      'Export to any format',
      'Custom templates',
    ],
    limits: {
      generationsPerDay: 100,
      maxProjects: -1,
    },
  },
  enterprise: {
    name: 'Enterprise',
    description: 'For large organizations',
    price: 99,
    priceId: process.env.STRIPE_ENTERPRISE_PRICE_ID || '',
    features: [
      'Unlimited generations',
      'Unlimited projects',
      'All AI models + fine-tuned models',
      '24/7 dedicated support',
      'API access',
      'Custom integrations',
      'SSO & team management',
    ],
    limits: {
      generationsPerDay: -1,
      maxProjects: -1,
    },
  },
}

export type PlanType = keyof typeof PLANS
