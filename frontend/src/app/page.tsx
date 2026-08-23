'use client';

import { useState } from 'react';
import { Search, Bot, Sparkles } from 'lucide-react';
import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Navigation */}
      <nav className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <Bot className="w-8 h-8 text-primary-600" />
              <span className="font-bold text-xl">VisualQA-Scraper</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/scrapers"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Scrapers
              </Link>
              <Link
                href="/query"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                Query
              </Link>
              <Link
                href="/scrapers/new"
                className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700 transition"
              >
                Create Scraper
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <div className="flex justify-center mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-primary-500/20 blur-3xl rounded-full"></div>
              <Sparkles className="relative w-16 h-16 text-primary-600" />
            </div>
          </div>
          
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Self-Healing Web Scrapers
            <br />
            <span className="text-primary-600">with Visual Understanding</span>
          </h1>
          
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Build scrapers that understand charts, tables, and infographics.
            When websites change, they repair themselves automatically.
          </p>

          <div className="flex justify-center space-x-4">
            <Link
              href="/scrapers/new"
              className="bg-primary-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-primary-700 transition shadow-lg shadow-primary-500/30"
            >
              Create Your First Scraper
            </Link>
            <Link
              href="/query"
              className="bg-white text-gray-900 px-8 py-3 rounded-lg font-medium hover:bg-gray-50 transition border border-gray-200"
            >
              Try Visual Query
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="mt-24 grid md:grid-cols-3 gap-8">
          <FeatureCard
            icon="🔄"
            title="Self-Healing"
            description="Scrapers automatically adapt when websites change layout or class names"
          />
          <FeatureCard
            icon="👁️"
            title="Visual Understanding"
            description="Extract data from charts, tables, and infographics using PixelRAG"
          />
          <FeatureCard
            icon="💬"
            title="Natural Language Queries"
            description="Ask questions about your scraped data in plain English"
          />
          <FeatureCard
            icon="⚡"
            title="Fast & Reliable"
            description="Built on Bright Data's infrastructure for speed and stability"
          />
          <FeatureCard
            icon="🎨"
            title="Clean UI"
            description="Beautiful interface for managing scrapers and exploring results"
          />
          <FeatureCard
            icon="🚀"
            title="Easy Deploy"
            description="One-click deployment to Vercel and Railway on free tier"
          />
        </div>

        {/* How It Works */}
        <div className="mt-24">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-4 gap-6">
            <StepCard
              number="1"
              title="Define"
              description="Describe what data you want in plain language"
            />
            <StepCard
              number="2"
              title="Scrape"
              description="Bright Data captures content with visual context"
            />
            <StepCard
              number="3"
              title="Index"
              description="PixelRAG indexes visual content for search"
            />
            <StepCard
              number="4"
              title="Query"
              description="Ask questions and get visual results"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="bg-white p-6 rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-lg transition">
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-gray-600 text-sm">{description}</p>
    </div>
  );
}

function StepCard({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 bg-primary-100 text-primary-600 rounded-full font-bold text-lg mb-4">
        {number}
      </div>
      <h3 className="font-semibold mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}
