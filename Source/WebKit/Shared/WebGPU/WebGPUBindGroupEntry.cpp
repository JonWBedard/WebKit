/*
 * Copyright (C) 2021-2023 Apple Inc. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY APPLE INC. AND ITS CONTRIBUTORS ``AS IS''
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL APPLE INC. OR ITS CONTRIBUTORS
 * BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "config.h"
#include "WebGPUBindGroupEntry.h"

#if ENABLE(GPU_PROCESS)

#include "WebGPUConvertFromBackingContext.h"
#include "WebGPUConvertToBackingContext.h"
#include <WebCore/WebGPUBindGroupEntry.h>
#include <WebCore/WebGPUExternalTexture.h>
#include <WebCore/WebGPUSampler.h>
#include <WebCore/WebGPUTexture.h>

namespace WebKit::WebGPU {

std::optional<BindGroupEntry> ConvertToBackingContext::convertToBacking(const WebCore::WebGPU::BindGroupEntry& bindGroupEntry)
{
    return WTF::switchOn(bindGroupEntry.resource, [&] (std::reference_wrapper<WebCore::WebGPU::Sampler> sampler) -> std::optional<BindGroupEntry> {
        auto identifier = convertToBacking(Ref { sampler.get() }.get());

        return { { bindGroupEntry.binding, { identifier }, identifier, BindingResourceType::Sampler } };
    }, [&] (std::reference_wrapper<WebCore::WebGPU::TextureView> textureView) -> std::optional<BindGroupEntry> {
        auto identifier = convertToBacking(Ref { textureView.get() }.get());

        return { { bindGroupEntry.binding, { identifier }, identifier, BindingResourceType::TextureView } };
    }, [&] (const auto& bufferBinding) -> std::optional<BindGroupEntry> {
        auto convertedBufferBinding = convertToBacking(bufferBinding);
        if (!convertedBufferBinding)
            return std::nullopt;

        return { { bindGroupEntry.binding, WTFMove(*convertedBufferBinding), convertedBufferBinding->buffer, BindingResourceType::BufferBinding } };
    }, [&] (std::reference_wrapper<WebCore::WebGPU::ExternalTexture> externalTexture) -> std::optional<BindGroupEntry> {
        auto identifier = convertToBacking(Ref { externalTexture.get() }.get());

        return { { bindGroupEntry.binding, { identifier }, identifier, BindingResourceType::ExternalTexture } };
    });
}

std::optional<WebCore::WebGPU::BindGroupEntry> ConvertFromBackingContext::convertFromBacking(const BindGroupEntry& bindGroupEntry)
{
    switch (bindGroupEntry.type) {
    case BindingResourceType::Sampler: {
        WeakPtr sampler = convertSamplerFromBacking(bindGroupEntry.identifier);
        if (!sampler)
            return std::nullopt;
        return { { bindGroupEntry.binding, { *sampler } } };
    }
    case BindingResourceType::TextureView: {
        WeakPtr textureView = convertTextureViewFromBacking(bindGroupEntry.identifier);
        if (!textureView)
            return std::nullopt;
        return { { bindGroupEntry.binding, { *textureView } } };
    }
    case BindingResourceType::BufferBinding: {
        auto bufferBinding = convertFromBacking(bindGroupEntry.bufferBinding);
        if (!bufferBinding)
            return std::nullopt;
        return { { bindGroupEntry.binding, { *bufferBinding } } };
    }
    case BindingResourceType::ExternalTexture: {
        auto externalTexture = convertExternalTextureFromBacking(bindGroupEntry.identifier);
        if (!externalTexture.get())
            return std::nullopt;
        return { { bindGroupEntry.binding, { *externalTexture.get() } } };
    }
    }

    RELEASE_ASSERT_NOT_REACHED();
}

} // namespace WebKit

#endif // ENABLE(GPU_PROCESS)
