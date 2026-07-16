"use client";

import { X } from "lucide-react";

import { Button } from "@/components/ui/button";

import { CategoryFilter } from "./CategoryFilter";
import { SearchBar } from "./SearchBar";
import { SortSelect } from "./SortSelect";
import { TagFilter } from "./TagFilter";
import type { Category, SortOption, Tag } from "./types";

interface FilterBarProps {
  categories: Category[];
  tags: Tag[];
  query: string;
  onQueryChange: (value: string) => void;
  categoryId: string | null;
  onCategoryChange: (categoryId: string | null) => void;
  tagIds: string[];
  onTagIdsChange: (tagIds: string[]) => void;
  sortOption: SortOption;
  onSortChange: (sortOption: SortOption) => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
}

export function FilterBar({
  categories,
  tags,
  query,
  onQueryChange,
  categoryId,
  onCategoryChange,
  tagIds,
  onTagIdsChange,
  sortOption,
  onSortChange,
  onClearFilters,
  hasActiveFilters,
}: FilterBarProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
      <SearchBar value={query} onChange={onQueryChange} />
      <div className="flex flex-wrap items-center gap-2">
        <CategoryFilter
          categories={categories}
          selectedCategoryId={categoryId}
          onChange={onCategoryChange}
        />
        <TagFilter tags={tags} selectedTagIds={tagIds} onChange={onTagIdsChange} />
        <SortSelect value={sortOption} onChange={onSortChange} />
        {hasActiveFilters && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClearFilters}
            className="gap-1.5"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Clear filters
          </Button>
        )}
      </div>
    </div>
  );
}
