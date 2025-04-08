import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Form, FormControl, FormField, FormItem, FormMessage } from "@/components/ui/form";

const formSchema = z.object({
  repoUrl: z.string().url("Please enter a valid URL").min(1, "Repository URL is required"),
});

type UrlInputProps = {
  onSubmit: (repoUrl: string) => void;
  isLoading: boolean;
};

export default function UrlInput({ onSubmit, isLoading }: UrlInputProps) {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      repoUrl: "",
    },
  });

  const handleSubmit = (values: z.infer<typeof formSchema>) => {
    onSubmit(values.repoUrl);
  };

  return (
    <div className="px-4 py-6 sm:px-0 mb-6">
      <Card>
        <CardContent className="pt-6">
          <h2 className="text-lg font-medium text-neutral-900 mb-4">Repository URL</h2>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-grow">
                  <FormField
                    control={form.control}
                    name="repoUrl"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <Input 
                            placeholder="https://github.com/organization/repository" 
                            {...field} 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <Button type="submit" disabled={isLoading}>
                  {isLoading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing...
                    </>
                  ) : (
                    "Check Compliance"
                  )}
                </Button>
              </div>
            </form>
          </Form>
          <p className="mt-2 text-sm text-neutral-500">Enter the GitHub repository URL to check compliance with OWASP standards and best practices.</p>
        </CardContent>
      </Card>
    </div>
  );
}
