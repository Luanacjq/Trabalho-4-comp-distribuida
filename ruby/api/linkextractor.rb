#!/usr/bin/env ruby
# encoding: utf-8

require "sinatra"
require "open-uri"
require "uri"
require "nokogiri"
require "json"
require "redis"

set :protection, :except=>:path_traversal
# Sinatra 4 bloqueia hosts desconhecidos; o front acessa a API como "api:4567"
set :host_authorization, { permitted_hosts: [] }

redis = Redis.new(url: ENV["REDIS_URL"] || "redis://localhost:6379")
# USE_CACHE=false desativa o Redis (cenario "sem cache" dos testes de desempenho)
use_cache = !%w[false 0 no].include?(ENV.fetch("USE_CACHE", "true").downcase)

Dir.mkdir("logs") unless Dir.exist?("logs")
cache_log = File.new("logs/extraction.log", "a")

get "/" do
  "Usage: http://<hostname>[:<prt>]/api/<url>"
end

get "/api/*" do
  url = [params['splat'].first, request.query_string].reject(&:empty?).join("?")
  cache_status = use_cache ? "HIT" : "OFF"
  jsonlinks = use_cache ? redis.get(url) : nil
  if jsonlinks.nil?
    cache_status = "MISS" if use_cache
    jsonlinks = JSON.pretty_generate(extract_links(url))
    redis.set(url, jsonlinks) if use_cache
  end

  cache_log.puts "#{Time.now.to_i}\t#{cache_status}\t#{url}"

  status 200
  headers "content-type" => "application/json"
  body jsonlinks
end

def extract_links(url)
  links = []
  doc = Nokogiri::HTML(URI.open(url))
  doc.css("a").each do |link|
    text = link.text.strip.split.join(" ")
    begin
      links.push({
        text: text.empty? ? "[IMG]" : text,
        href: URI.join(url, link["href"])
      })
    rescue
    end
  end
  links
end
